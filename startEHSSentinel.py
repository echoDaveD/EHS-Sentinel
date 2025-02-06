import asyncio
import serial
import serial_asyncio
import traceback
from MessageProcessor import MessageProcessor
from EHSArguments import EHSArguments
from EHSConfig import EHSConfig
from EHSExceptions import MessageWarningException
from MQTTClient import MQTTClient
import aiofiles
import json
import struct

# Get the logger
from CustomLogger import logger, setSilent

version = "0.1SNAPSHOT"

class SerialReader(asyncio.Protocol):
    """
    SerialReader is an asyncio.Protocol implementation that reads data from a serial connection and appends it to a buffer.
    Attributes:
        buffer (list): A list to store the received bytes.
    Methods:
        data_received(data):
            Called when data is received. Appends each byte of the received data to the buffer.
    """
    
    def __init__(self, buffer):
        self.buffer = buffer

    def data_received(self, data):
        self.buffer.extend(data)

async def main():
    """
    Main function to start the EHSSentinel application.
    This function initializes logging, reads command-line arguments and configuration,
    and processes messages either from a dump file (in dry run mode) or from a serial port.
    Steps:
    1. Logs the startup banner and version information.
    2. Reads command-line arguments.
    3. Reads configuration settings.
    4. If a dump file is specified and not in dry run mode, opens the dump file for writing.
    5. If in dry run mode, reads messages from the dump file and processes them.
    6. If not in dry run mode, reads messages from the serial port.
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

    # if Silent is true, set Silent Mode
    if config.GENERAL['silentMode']:
        setSilent()

    mqtt = MQTTClient(broker=config.MQTT['broker-url'], 
                      port=config.MQTT['broker-port'], 
                      topicPrefix=config.MQTT['topicPrefix'],
                      useHassFormat=config.MQTT['useHassFormat'],
                      client_id=config.MQTT['client-id'], 
                      username=config.MQTT['user'], 
                      password=config.MQTT['password'])

    # if dryrun then we read from dumpfile
    if args.DRYRUN:
        logger.info(f"DRYRUN detected, reading from dumpfile {args.DUMPFILE}")
        async with aiofiles.open(args.DUMPFILE, mode='r') as file:
            async for line in file:
                line = json.loads(line.strip())
                await process_message(line, args)
    else:
        # we are not in dryrun mode, so we need to read from Serial Pimort
        await serialRead(config, args)

async def process_buffer(buffer, args):
    """
    Continuously processes a buffer of bytes to extract and handle messages.
    This function runs an infinite loop that checks the buffer for messages starting with a specific start byte (0x32).
    When a start byte is found, it reads the packet size from the next two bytes, constructs the message, and processes it.
    If the start byte is not found, it removes the first byte from the buffer and continues.
    Args:
        buffer (list): A list of bytes representing the buffer to be processed.
    Notes:
        - The function assumes that the buffer contains bytes in the correct order.
        - The function uses asyncio.sleep(0.1) to yield control and allow other tasks to run.
        - The function logs various debug messages to help trace the processing steps.
    """

    while True:
        if buffer:
            logger.debug(f"Buffersize: {len(buffer)}")
            if buffer[0] == 0x32:
                logger.debug("Start Byte recognized")
                packet_size = ((buffer[1] << 8) | buffer[2]) +2
                logger.debug(f"Readed packet size: {packet_size-1}")
                if len(buffer) > packet_size-1:
                    message = []
                    for i in range(0, len(buffer)):
                        message.append(buffer[i])
                        if i == packet_size-1: #buffer[i] == 0x34  or
                            hex_message = list(map(hex, message))
                            logger.debug(f"Complete Message: {i}/{packet_size-1}")
                            logger.debug(f"Last Byte readed: {hex(buffer[i])}")
                            logger.debug(f"message raw: {message}")
                            logger.debug(f"        hex: {hex_message}")
                            await process_message(message, args)
                            del buffer[0:i]
                            break
                else:
                    logger.debug(f"Buffer to small to read hole packet, wait... buffer size {len(buffer)} packet size {packet_size}")
            else:
                logger.debug(f"Received byte not a startbyte 0x32 {buffer[0]} / {hex(buffer[0])}")
                buffer.pop(0)

        await asyncio.sleep(0.03)

async def serialRead(config, args):
    """
    Asynchronously reads data from a serial port and processes it.
    This function opens a serial port connection using the `serial_asyncio` library,
    reads data into a buffer, and starts an asynchronous task to process the buffer.
    It runs indefinitely until interrupted by a KeyboardInterrupt, at which point it
    closes the serial port and any open dump writer.
    Args:
        None
    Returns:
        None
    Raises:
        KeyboardInterrupt: If the user interrupts the process with a keyboard signal.
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
    asyncio.create_task(process_buffer(buffer, args))# start the async buffer process
    # start the async writer process
    asyncio.create_task(serial_write(writer, reader))

    # Read loop
    while True:
        data = await reader.readline()  # Read up to 100 bytes
        if data:
            buffer.extend(data)
            logger.debug(f"Received: {[hex(x) for x in data]}")

async def serial_write(writer, reader):
    """
    Asynchronously writes data to the serial port.
    This function sends data through the serial port at regular intervals.
    Args:
        transport: The serial transport object.
        args: Additional arguments.
    Returns:
        None
    """
    while True:
        await asyncio.sleep(30)
        # Example data to write
        
        packet = bytearray([
            0x32,  # Packet Start Byte
            0x00, 0x12,  # Packet Size
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
        
        # Compute CRC16 for packet (excluding start and end bytes)
        crc = calculate_crc16(packet)
        packet.extend(struct.pack('<H', crc))  # Append CRC16 (little-endian)
        packet.append(0x34)  # Packet End Byte
        writer.write(packet)
        await writer.drain()
        logger.info(f"Sent data raw: {packet}")
        logger.info(f"Sent data raw: {[hex(x) for x in packet]}")
        try:
            response = await reader.readuntil(b'\x34')  # Read until 0x34
            logger.debug(f"Sent Data Response: {[hex(x) for x in response]}")
        except asyncio.TimeoutError:
            logger.debug("No response received within timeout")
        await asyncio.sleep(1)  # Adjust the interval as needed
        

def calculate_crc16(data: bytes) -> int:
    """Calculate CRC16 using the standard CRC-16-CCITT (0xFFFF) polynomial."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

async def process_message(buffer, args):
    """
    Asynchronously processes a message buffer.
    If `dumpWriter` is `None`, it attempts to process the message using `MessageProcessor`.
    If a `MessageWarningException` is raised, it logs a warning and skips the message.
    If any other exception is raised, it logs an error, skips the message, and logs the stack trace.
    If `dumpWriter` is not `None`, it writes the buffer to `dumpWriter`.
    Args:
        buffer (bytes): The message buffer to be processed.
    """

    if args.DUMPFILE and not args.DRYRUN:
        async with aiofiles.open(args.DUMPFILE, "a") as dumpWriter:
           await dumpWriter.write(f"{buffer}\n")
    else:
        try:
            messageProcessor = MessageProcessor()
            messageProcessor.process_message(buffer)    
        except MessageWarningException as e:
            logger.warning("Warnung accured, Message will be skipped")
            logger.warning(f"Error processing message: {e}")
        except Exception as e:
            logger.error("Error Accured, Message will be skipped")
            logger.error(f"Error processing message: {e}")
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())