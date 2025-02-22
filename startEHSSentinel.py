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
import struct
import binascii

# Get the logger
from CustomLogger import logger
from NASAPacket import NASAPacket, AddressClassEnum, PacketType, DataType
from NASAMessage import NASAMessage

version = "0.2.0 Stable"

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
        config (object): Configuration object containing serial connection parameters.
        args (object): Additional arguments for buffer processing.
    This function establishes a serial connection using parameters from the config object,
    reads data from the serial port until a specified delimiter (0x34) is encountered,
    and appends the received data to a buffer. It also starts an asynchronous task to
    process the buffer.
    The serial connection is configured with the following parameters:
        - Device URL: config.SERIAL['device']
        - Baudrate: config.SERIAL['baudrate']
        - Parity: Even
        - Stopbits: One
        - Bytesize: Eight
        - RTS/CTS flow control: Enabled
        - Timeout: 0
    The function runs an infinite loop to continuously read data from the serial port.
    """

    buffer = []
    loop = asyncio.get_running_loop()

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
            #serial_write(writer, reader, args),
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

async def serial_write(writer:asyncio.StreamWriter, reader: asyncio.StreamReader, args):
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
    while True:
        await asyncio.sleep(5)
        # Example data to write
        
        decoded_nasa = NASAPacket()
        decoded_nasa.set_packet_source_address_class(AddressClassEnum.WiFiKit)
        decoded_nasa.set_packet_source_channel(0)
        decoded_nasa.set_packet_source_address(144)
        decoded_nasa.set_packet_dest_address_class(AddressClassEnum.BroadcastSetLayer)
        decoded_nasa.set_packet_dest_channel(0)
        decoded_nasa.set_packet_dest_address(32)
        decoded_nasa.set_packet_information(True)
        decoded_nasa.set_packet_version(2)
        decoded_nasa.set_packet_retry_count(0)
        decoded_nasa.set_packet_type(PacketType.Normal)
        decoded_nasa.set_packet_data_type(DataType.Read)
        decoded_nasa.set_packet_number(3)
        lst = []
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x4093)
        tmp_msg.set_packet_message_type(0)
        tmp_msg.set_packet_payload([0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x4094)
        tmp_msg.set_packet_message_type(0)
        tmp_msg.set_packet_payload([0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x4273)
        tmp_msg.set_packet_message_type(1)
        tmp_msg.set_packet_payload([0, 0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x4274)
        tmp_msg.set_packet_message_type(1)
        tmp_msg.set_packet_payload([0, 0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x4275)
        tmp_msg.set_packet_message_type(1)
        tmp_msg.set_packet_payload([0, 0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x4276)
        tmp_msg.set_packet_message_type(1)
        tmp_msg.set_packet_payload([0, 0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x4277)
        tmp_msg.set_packet_message_type(1)
        tmp_msg.set_packet_payload([0, 0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x4278)
        tmp_msg.set_packet_message_type(1)
        tmp_msg.set_packet_payload([0, 0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x4279)
        tmp_msg.set_packet_message_type(1)
        tmp_msg.set_packet_payload([0, 0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x427a)
        tmp_msg.set_packet_message_type(1)
        tmp_msg.set_packet_payload([0, 0])
        lst.append(tmp_msg)
        tmp_msg = NASAMessage()
        tmp_msg.set_packet_message(0x427b)
        tmp_msg.set_packet_message_type(1)
        tmp_msg.set_packet_payload([0, 0])
        lst.append(tmp_msg)
        decoded_nasa.set_packet_messages(lst)
        final_packet = decoded_nasa.to_raw()
        writer.write(final_packet)
        await writer.drain()
        logger.info(f"Sent data raw: {final_packet}")
        logger.info(f"Sent data raw: {decoded_nasa}")
        logger.info(f"Sent data raw: {[hex(x) for x in final_packet]}")
        logger.info(f"Sent data raw: {[x for x in final_packet]}")

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