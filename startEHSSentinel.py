import asyncio
import serial
import serial_asyncio
import traceback
from MessageProcessor import MessageProcessor
from EHSArguments import EHSArguments
from EHSConfig import EHSConfig
from EHSExceptions import MessageWarningException, MessageCapacityStructureWarning
from MQTTClient import MQTTClient
import aiofiles
import json
import struct
import binascii

# Get the logger
from CustomLogger import logger, setSilent
from NASAPacket import NASAPacket

version = "0.1.0 Stable"

async def main():
    """
    Main function to start the EHS Sentinel application.
    This function performs the following steps:
    1. Logs the startup banner and version information.
    2. Reads command-line arguments.
    3. Reads configuration settings.
    4. Connects to the MQTT broker.
    5. Sets silent mode if specified in the configuration.
    6. If dry run mode is enabled, reads data from a dump file and processes it.
    7. If not in dry run mode, reads data from a serial port and processes it.
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

    # if Silent is true, set Silent Mode
    if config.GENERAL['silentMode']:
        setSilent()

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
                await process_packet(line, args)
    else:
        # we are not in dryrun mode, so we need to read from Serial Pimort
        await serial_read(config, args)

async def process_buffer(buffer, args):
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
                        asyncio.create_task(process_packet(buffer[i:], args))
                    else:
                        logger.debug(f"Buffermessages to short for NASA {len(buffer)}")
                    break
        else:
            logger.debug(f"Buffer to short for NASA {len(buffer)}")

async def serial_read(config, args):
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
                    timeout=0
    )

    # start the async buffer process
    #asyncio.create_task(process_buffer(buffer, args))# start the async buffer process
   
    # TODO have to be tested and verified, please do not try it yet
    # start the async writer process
    asyncio.create_task(serial_write(writer, reader))

    # Read loop
    while True:
        data = await reader.readuntil(b'\x34')  # Read up to end of next message 0x34
        if data:
            asyncio.create_task(process_buffer(data, args))
            #buffer.extend(data)
            logger.debug(f"Received: {[hex(x) for x in data]}")

async def serial_write(writer, reader):
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
        
        packet = bytearray([
            #0x32,  # Packet Start Byte
            #0x00, 0x12,  # Packet Size
            0x80,  # Source Address Class JIGTester
            0xFF,  # Source Channel
            0x00,  # Source Address
            0x20,  # Destination Address Class Indoor
            0x00,  # Destination Channel
            0x00,  # Destination Address
            0xC0,  # Packet Information + Protocol Version + Retry Count
            0x11,  # Packet Type [Normal = 1] + Data Type [Read = 1]
            0xF0,  # Packet Number
            0x01,  # Capacity (Number of Messages)
            0x42, 0x56,  # NASA Message Number
            0x00, 0x00  # Message Payload (placeholder for return value)
        ])

        crc=binascii.crc_hqx(packet, 0)
        # NOTE: include length of CRC(2) and length of length field(2) in the 
        #       total length, exclude SF/TF of total length 
        final_packet = struct.pack(">BH", 0x32, len(packet)+2+2) + packet + struct.pack(">HB", crc, 0x34)
        # ['0x32', '0x0', '0x12', '0x80', '0xff', '0x0', '0x20', '0x0', '0x0', '0xc0', '0x11', '0xf0', '0x1', '0x42', '0x56', '0x0', '0x0', '0xf9', '0x65', '0x34']
        # ['0x32', '0x0', '0x12', '0x80', '0xff', '0x0', '0x20', '0x0', '0x0', '0xc0', '0x11', '0xf0', '0x1', '0x42', '0x56', '0x0', '0x0', '0x38', '0xc6', '0x34']
        writer.write(final_packet)
        await writer.drain()
        logger.info(f"Sent data raw: {final_packet}")
        logger.info(f"Sent data raw: {[hex(x) for x in final_packet]}")
        await asyncio.sleep(1)  # Adjust the interval as needed

async def process_packet(buffer, args):
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
            messageProcessor = MessageProcessor()
            messageProcessor.process_message(nasa_packet)    
        except ValueError as e:
            logger.warning("Value Error on parsing Packet, Packet will be skipped")
            logger.warning(f"Error processing message: {e}")
            logger.warning(f"Complete Packet: {[hex(x) for x in buffer]}")
        except MessageCapacityStructureWarning as e:
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