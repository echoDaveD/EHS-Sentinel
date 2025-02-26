import asyncio
import serial
import serial_asyncio
import traceback
from MessageProcessor import MessageProcessor
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

version = "0.3.0 Stable"

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
    """
    Processes a buffer of data asynchronously, identifying and handling packets based on specific criteria.
    Args:
        buffer (list): A list of bytes representing the buffer to be processed.
        args (Any): Additional arguments to be passed to the packet processing function.
    Notes:
        - The function continuously checks the buffer for data.
        - If the first byte of the buffer is 0x32, it is considered a start byte.
        - The packet size is determined by combining the second and third bytes of the buffer.
        - If the buffer contains enough data for a complete packet, the packet is processed.
        - If the buffer does not contain enough data, the function waits and checks again.
        - Non-start bytes are removed from the buffer.
        - The function sleeps for 0.03 seconds between iterations to avoid busy-waiting.
    Logging:
        - Logs the buffer size when data is present.
        - Logs when the start byte is recognized.
        - Logs the calculated packet size.
        - Logs the complete packet and the last byte read when a packet is processed.
        - Logs if the buffer is too small to read a complete packet.
        - Logs if a received byte is not a start byte.
    """

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
    """
    Asynchronously reads data from a serial connection and processes it.
    Args:
        config (object): Configuration object containing serial or tcp connection parameters.
        args (object): Additional arguments for buffer processing.
    This function establishes a serial or tcp connection using parameters from the config object,
    reads data from the serial port or tcp port until a specified delimiter (0x34) is encountered,
    and appends the received data to a buffer. It also starts an asynchronous task to
    process the buffer.
    The function runs an infinite loop to continuously read data from the serial port/tcp port.
    """

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
            serial_write(writer, reader, args, config),
        )


async def serial_read(reader, args, config):
    while True:
        data = await reader.readuntil(b'\x34')  # Read up to end of next message 0x34
        if data:
            asyncio.create_task(process_buffer(data, args, config))
            #buffer.extend(data)
            logger.debug(f"Received: {data}")
            logger.debug(f"Received: {data!r}")
            logger.debug(f"Received: {[hex(x) for x in data]}")

        await asyncio.sleep(0.1)  # Yield control to other tasks

async def serial_write(writer:asyncio.StreamWriter, reader: asyncio.StreamReader, args, config):
    """
    TODO Not used yet, only for future use...


    Asynchronously writes data to the serial port.
    This function sends data through the serial port at regular intervals.
    Args:
        transport: The serial transport object.
        args: Additional arguments.
    Returns:
        None
    """
    if config.POLLING is not None:
        for poller in config.POLLING['fetch_interval']:
            if poller['enable']:
                await asyncio.sleep(3)
                asyncio.create_task(make_default_request_packet(writer=writer, config=config, poller=poller))

async def make_default_request_packet(writer, config, poller):
    logger.info(f"Setting up Poller {poller['name']} every {poller['schedule']} seconds")
    message_list = []
    for message in config.POLLING['groups'][poller['name']]:
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(int(config.NASA_REPO[message]['address'], 16))
        if config.NASA_REPO[message]['type'] == 'ENUM':
            tmp_msg.set_packet_message_type(0)
            tmp_msg.set_packet_payload([0])
        elif config.NASA_REPO[message]['type'] == 'VAR':
            tmp_msg.set_packet_message_type(1)
            tmp_msg.set_packet_payload([0, 0])
        elif config.NASA_REPO[message]['type'] == 'LVAR':
            tmp_msg.set_packet_message_type(2)
            tmp_msg.set_packet_payload([0, 0, 0, 0])
        else:
            logger.warning(f"Unknown Type for {message} type: {config.NASA_REPO[message]['type']}")
            break
        message_list.append(tmp_msg)

    while True:
        chunk_size = 10
        chunks = [message_list[i:i + chunk_size] for i in range(0, len(message_list), chunk_size)]
        for chunk in chunks:
            await asyncio.sleep(1)
            nasa_msg = NASAPacket()
            nasa_msg.set_packet_source_address_class(AddressClassEnum.WiFiKit)
            nasa_msg.set_packet_source_channel(0)
            nasa_msg.set_packet_source_address(144)
            nasa_msg.set_packet_dest_address_class(AddressClassEnum.BroadcastSetLayer)
            nasa_msg.set_packet_dest_channel(0)
            nasa_msg.set_packet_dest_address(32)
            nasa_msg.set_packet_information(True)
            nasa_msg.set_packet_version(2)
            nasa_msg.set_packet_retry_count(0)
            nasa_msg.set_packet_type(PacketType.Normal)
            nasa_msg.set_packet_data_type(DataType.Read)
            nasa_msg.set_packet_number(len(chunk))
            nasa_msg.set_packet_messages(chunk)
            final_packet = nasa_msg.to_raw()
            writer.write(final_packet)
            await writer.drain()
            if config.LOGGING['pollerMessage']:
                logger.info(f"Polling following raw: {[hex(x) for x in final_packet]}")
                logger.info(f"Polling following NASAPacket: {nasa_msg}")
            else:
                logger.debug(f"Sent data raw: {final_packet}")
                logger.debug(f"Sent data raw: {nasa_msg}")
                logger.debug(f"Sent data raw: {[hex(x) for x in final_packet]}")
                logger.debug(f"Sent data raw: {[x for x in final_packet]}")

        await asyncio.sleep(poller['schedule'])
        logger.info(f"Refresh Poller {poller['name']}")

async def process_packet(buffer, args, config):
    """
    Asynchronously processes a packet buffer.
    If `dumpWriter` is `None`, it attempts to process the packet using `MessageProcessor`.
    If a `MessageWarningException` is raised, it logs a warning and skips the packet.
    If any other exception is raised, it logs an error, skips the packet, and logs the stack trace.
    If `dumpWriter` is not `None`, it writes the buffer to `dumpWriter`.
    Args:
        buffer (bytes): The packet buffer to be processed.
    """

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
                messageProcessor.process_message(nasa_packet)    
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
        except SkipInvalidPacketException as e:
            logger.debug("Warnung accured, Packet will be skipped")
            logger.debug(f"Error processing message: {e}")
            logger.debug(f"Complete Packet: {[hex(x) for x in buffer]}")
        except MessageWarningException as e:
            logger.warning("Warnung accured, Packet will be skipped")
            logger.warning(f"Error processing message: {e}")
            logger.warning(f"Complete Packet: {[hex(x) for x in buffer]}")
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