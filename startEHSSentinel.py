import asyncio
import serial
import serial_asyncio
import traceback
from MessageProcessor import MessageProcessor
from MessageProducer import MessageProducer
from EHSArguments import EHSArguments
from EHSConfig import EHSConfig
from EHSExceptions import MessageWarningException, SkipInvalidPacketException
from MQTTClient import MQTTClient
import aiofiles
import json
import random

# Get the logger
from CustomLogger import logger
from NASAPacket import NASAPacket, AddressClassEnum, PacketType, DataType
from NASAMessage import NASAMessage

version = "1.0.0 Stable"

async def main():
    """
    Main function to start the EHS Sentinel application.
    This function performs the following steps:
    1. Logs the startup banner and version information.
    2. Reads command-line arguments.
    3. Reads configuration settings.
    4. Connects to the MQTT broker.
    5. If dry run mode is enabled, reads data from a dump file and processes it.
    6. If not in dry run mode, reads data from a serial port and processes it.
    Args:
        None
    Returns:
        None
    """

    logger.info("####################################################################################################################")
    logger.info("#                                                                                                                  #")
    logger.info("#    ######   ##  ##   #####             #####    ######  ##   ##  ########  ######  ##   ##   ######   ##         #")
    logger.info("#    ##   #   ##  ##  ##   ##           ##   ##   ##   #  ###  ##  ## ## ##    ##    ###  ##   ##   #   ##         #")
    logger.info("#    ##       ##  ##  ##                ##        ##      #### ##     ##       ##    #### ##   ##       ##         #")
    logger.info("#    ####     ######   #####             #####    ####    #######     ##       ##    #######   ####     ##         #")
    logger.info("#    ##       ##  ##       ##                ##   ##      ## ####     ##       ##    ## ####   ##       ##         #")
    logger.info("#    ##   #   ##  ##  ##   ##           ##   ##   ##   #  ##  ###     ##       ##    ##  ###   ##   #   ##         #")
    logger.info("#    ######   ##  ##   #####             #####    ######  ##   ##    ####    ######  ##   ##   ######   #######    #")
    logger.info("#                                                                                                                  #")
    logger.info("####################################################################################################################")
    logger.info(f"Starting EHSSentinel {version} written by echoDave")
    logger.info("")

    logger.info("Reading Arguments ...")
    args = EHSArguments()

    logger.info("Reading Configuration ...")
    config = EHSConfig()

    logger.info("connecting to MQTT Borker ...")
    mqtt = MQTTClient()
    await mqtt.connect()

    await asyncio.sleep(1)

    # if dryrun then we read from dumpfile
    if args.DRYRUN:
        logger.info(f"DRYRUN detected, reading from dumpfile {args.DUMPFILE}")
        async with aiofiles.open(args.DUMPFILE, mode='r') as file:
            async for line in file:
                try:
                    line = json.loads(line.strip()) # for [12, 234, 456 ,67]
                except:
                    line = line.strip().replace("'", "").replace("[", "").replace("]", "").split(", ") # for ['0x1', '0x2' ..]
                    line = [int(value, 16) for value in line]
                await process_packet(line, args, config)
    else:
        # we are not in dryrun mode, so we need to read from Serial Pimort
        await serial_connection(config, args)

async def process_buffer(buffer, args, config):
    if buffer:
        if (len(buffer) > 14):
            for i in range(0, len(buffer)):
                if buffer[i] == 0x32:
                    if (len(buffer[i:]) > 14):
                        asyncio.create_task(process_packet(buffer[i:], args, config))
                    else:
                        logger.debug(f"Buffermessages to short for NASA {len(buffer)}")
                    break
        else:
            logger.debug(f"Buffer to short for NASA {len(buffer)}")

async def serial_connection(config, args):
    buffer = []
    loop = asyncio.get_running_loop()

    if config.TCP is not None:
        reader, writer = await asyncio.open_connection(config.TCP['ip'], config.TCP['port'])
    else:
        reader, writer = await serial_asyncio.open_serial_connection(
                        loop=loop, 
                        url=config.SERIAL['device'], 
                        baudrate=config.SERIAL['baudrate'], 
                        parity=serial.PARITY_EVEN,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,
                        rtscts=True,
                        timeout=1
        )
        
    await asyncio.gather(
            serial_read(reader, args, config),
            serial_write(writer, config),
        )

async def serial_read(reader: asyncio.StreamReader, args, config):
    prev_byte = 0x00
    packet_started = False
    data = bytearray()
    packet_size = 0

    while True:
        current_byte = await reader.read(1)  # read bitewise
        #data = await reader.read(1024)
        #data = await reader.readuntil(b'\x34fd')
        if current_byte:
            if packet_started:
                data.extend(current_byte)
                if len(data) == 3:
                    packet_size = ((data[1] << 8) | data[2]) + 2
    
                if packet_size <= len(data):
                    if current_byte == b'\x34':
                        asyncio.create_task(process_buffer(data, args, config))
                        logger.debug(f"Received int: {data}")
                        logger.debug(f"Received hex: {[hex(x) for x in data]}")
                        data = bytearray()
                        packet_started = False
                    else:
                        if config.LOGGING['invalidPacket']:
                            logger.warning(f"Packet does not end with an x34. Size {packet_size} length {len(data)}")
                            logger.warning(f"Received hex: {[hex(x) for x in data]}")
                            logger.warning(f"Received raw: {data}")
                        else:
                            logger.debug(f"Packet does not end with an x34. Size {packet_size} length {len(data)}")
                            logger.debug(f"Received hex: {[hex(x) for x in data]}")
                            logger.debug(f"Received raw: {data}")
                        
                        data = bytearray()
                        packet_started = False

            # identify packet start
            if current_byte == b'\x00' and prev_byte == b'\x32':
                packet_started = True
                data.extend(prev_byte)
                data.extend(current_byte)

            prev_byte = current_byte

        #await asyncio.sleep(0.001)  # Yield control to other tasks


async def serial_write(writer:asyncio.StreamWriter, config):
    producer = MessageProducer(writer=writer)

    # Wait 20s befor initial polling
    await asyncio.sleep(20)

    if config.POLLING is not None:
        for poller in config.POLLING['fetch_interval']:
            if poller['enable']:
                await asyncio.sleep(1)
                asyncio.create_task(make_default_request_packet(producer=producer, config=config, poller=poller))

async def make_default_request_packet(producer: MessageProducer, config: EHSConfig, poller):
    logger.info(f"Setting up Poller {poller['name']} every {poller['schedule']} seconds")
    message_list = []
    for message in config.POLLING['groups'][poller['name']]:
        message_list.append(message)

    while True:
        try:
            await producer.read_request(message_list)
        except MessageWarningException as e:
            logger.warning("Polling Messages was not successfull")
            logger.warning(f"Error processing message: {e}")
            logger.warning(f"Message List: {message_list}")
        except Exception as e:
            logger.error("Error Accured, Polling will be skipped")
            logger.error(f"Error processing message: {e}")
            logger.error(traceback.format_exc())
        await asyncio.sleep(poller['schedule'])
        logger.info(f"Refresh Poller {poller['name']}")

async def process_packet(buffer, args, config):
    if args.DUMPFILE and not args.DRYRUN:
        async with aiofiles.open(args.DUMPFILE, "a") as dumpWriter:
           await dumpWriter.write(f"{buffer}\n")
    else:
        try:
            nasa_packet = NASAPacket()
            nasa_packet.parse(buffer)
            logger.debug("Packet processed: ")
            logger.debug(f"Packet raw: {[hex(x) for x in buffer]}")
            logger.debug(nasa_packet)
            if nasa_packet.packet_source_address_class in (AddressClassEnum.Outdoor, AddressClassEnum.Indoor):
                messageProcessor = MessageProcessor()
                await messageProcessor.process_message(nasa_packet)    
            elif nasa_packet.packet_source_address_class == AddressClassEnum.WiFiKit and \
                nasa_packet.packet_dest_address_class == AddressClassEnum.BroadcastSelfLayer and \
                nasa_packet.packet_data_type == DataType.Notification:
                pass
            else:
                if config.LOGGING['packetNotFromIndoorOutdoor']:
                    logger.info("Message not From Indoor or Outdoor") 
                    logger.info(nasa_packet)
                    logger.info(f"Packet int: {[x for x in buffer]}")
                    logger.info(f"Packet hex: {[hex(x) for x in buffer]}")
                else:
                    logger.debug("Message not From Indoor or Outdoor") 
                    logger.debug(nasa_packet)
                    logger.debug(f"Packet int: {[x for x in buffer]}")
                    logger.debug(f"Packet hex: {[hex(x) for x in buffer]}")
        except ValueError as e:
            logger.warning("Value Error on parsing Packet, Packet will be skipped")
            logger.warning(f"Error processing message: {e}")
            logger.warning(f"Complete Packet: {[hex(x) for x in buffer]}")
            logger.warning(traceback.format_exc())
        except SkipInvalidPacketException as e:
            logger.debug("Warnung accured, Packet will be skipped")
            logger.debug(f"Error processing message: {e}")
            logger.debug(f"Complete Packet: {[hex(x) for x in buffer]}")
            logger.debug(traceback.format_exc())
        except MessageWarningException as e:
            logger.warning("Warnung accured, Packet will be skipped")
            logger.warning(f"Error processing message: {e}")
            logger.warning(f"Complete Packet: {[hex(x) for x in buffer]}")
            logger.warning(traceback.format_exc())
        except Exception as e:
            logger.error("Error Accured, Packet will be skipped")
            logger.error(f"Error processing message: {e}")
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")