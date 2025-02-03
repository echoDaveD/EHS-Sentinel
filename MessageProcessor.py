import asyncio
import logging
import traceback
import yaml
from CustomLogger import logger, setSilent
from EHSArguments import EHSArguments
from EHSConfig import EHSConfig
from EHSExceptions import MessageWarningException
from enum import Enum

class SoureAddressEnum(Enum):
    """
    Enum class representing various source addresses for the EHS-Sentinel Message Processor.
    """

    Outdoor = 0x10
    HTU = 0x11
    Indoor = 0x20
    ERV = 0x30
    Diffuser = 0x35
    MCU = 0x38
    RMC = 0x40
    WiredRemote = 0x50
    PIM = 0x58
    SIM = 0x59
    Peak = 0x5A
    PowerDivider = 0x5B
    OnOffController = 0x60
    WiFiKit = 0x62
    CentralController = 0x65
    DMS = 0x6A
    JIGTester = 0x80
    BroadcastSelfLayer = 0xB0
    BroadcastControlLayer = 0xB1
    BroadcastSetLayer = 0xB2
    BroadcastCS = 0xB3
    BroadcastControlAndSetLayer = 0xB3
    BroadcastModuleLayer = 0xB4
    BroadcastCSM = 0xB7
    BroadcastLocalLayer = 0xB8
    BroadcastCSML = 0xBF
    Undefined = 0xFF

class MessageProcessor:
    """
    The MessageProcessor class is responsible for handling and processing incoming messages for the EHS-Sentinel system.
    It follows the singleton pattern to ensure only one instance is created. The class provides methods to process
    messages, extract submessages, search for message definitions in a configuration repository, and determine the
    value of message payloads based on predefined rules. It also includes logging for debugging and tracing the
    message processing steps.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Create a new instance of the class if one does not already exist.
        This method ensures that only one instance of the class is created (singleton pattern).
        If an instance already exists, it returns the existing instance.
        Args:
            cls (type): The class being instantiated.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Returns:
            MessageProcessor: The single instance of the MessageProcessor class.
        """
        if not cls._instance:
            cls._instance = super(MessageProcessor, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initializes the MessageProcessor instance.
        This constructor checks if the instance has already been initialized to prevent reinitialization.
        If not initialized, it sets the _initialized flag to True, logs the initialization process,
        and initializes the configuration and argument handling components.
        Attributes:
            _initialized (bool): A flag indicating whether the instance has been initialized.
            config (EHSConfig): An instance of the EHSConfig class for configuration management.
            args (EHSArguments): An instance of the EHSArguments class for argument handling.
        """
        if self._initialized:
            return
        self._initialized = True
        logger.debug("init MessageProcessor")
        self.config = EHSConfig()
        self.args = EHSArguments()

    def process_message(self, message):
        """
        Processes an incoming message by verifying its structure, extracting relevant data, and logging the results.
        Args:
            message (list): A list of integers representing the message bytes.
        Raises:
            MessageWarningException: If the message is invalid due to missing end byte, incorrect length, or other processing errors.
        Logs:
            Various debug and info logs to trace the processing steps, including packet size, raw and hex message content, source address, capacity, and extracted message details.
        """

        packet_size = ((message[1] << 8) | message[2]) + 2
        logger.debug(f"Packet size caluclated/readed: {len(message)}/{packet_size}")
        logger.debug(f"Processing message raw: {list(map(lambda x: f'{x:<4}', message))}")
        logger.debug(f"Processing message hex: {list(map(lambda x: f'{hex(x):<4}', message))}")
        logger.debug(f"Source Address rasw: {message[3]} hex: {hex(message[3])}")
        sourceAdress = SoureAddressEnum(message[3])
        logger.debug(f"Source Address: {sourceAdress}")

        # verify end byte
        if message[-1] != 0x34:
            logger.debug("Invalid message, missing end byte")
            raise MessageWarningException(argument=hex(message[-1]), message="Invalid message, missing or wrong end byte")
        
        # verify length of message
        if len(message) < 14:
            raise MessageWarningException(argument=len(message), message="Invalid message, message to short")
        
        # Extract Capacity
        capacity = message[12]
        logger.debug(f"Message has a Capacity of: {capacity}/{hex(capacity)}")

        list_of_messages = self.extract_messages(1, capacity, message[13:-3], [])
        for msg in list_of_messages:
            msgname = self.search_nasa_table(hex(msg['message_number']))
            if msgname is not None:
                try:
                    msgvalue = self.determine_value(msg['payload'], msgname)
                except Exception as e:
                    raise MessageWarningException(argument=msg['payload'], message=f"Value of {hex(msg['message_number']):<6} couldn't be determinate, skip Message {e}")
                self.protocolMessage(msg, msgname, msgvalue)
            else:
                logger.warning(f"Message not Found in NASA repository: {hex(msg['message_number']):<6} Type: {msg['message_type']} Payload: {msg['payload']}")

    def protocolMessage(self, msg, msgname, msgvalue):
        logger.info(f"Message number: {hex(msg['message_number']):<6} {msgname:<50} Type: {msg['message_type']} Payload: {msgvalue}")

        if self.config.GENERAL['protocolFile'] is not None:
            with open(self.config.GENERAL['protocolFile'], "a") as protWriter:
                protWriter.write(f"{hex(msg['message_number']):<6},{msgname:<50},{msg['message_type']},{msgvalue}\n")

        if not self.args.DRYRUN:
            #TODO mqtt publisher here
            pass


    def search_nasa_table(self, address):
        """
        Searches for a specific address in the NASA_REPO configuration and returns the corresponding key.
        Args:
            address (str): The address to search for in the NASA_REPO.
        Returns:
            str: The key associated with the given address if found, otherwise None.
        """

        for key, value in self.config.NASA_REPO.items():
            if value['address'].lower() == address:
                return key
    
    def extract_messages(self, depth, capacity, msg_rest, return_list):
        """
        Recursively extracts submessages from a given message list and appends them to the return list.
        Args:
            depth (int): The current depth of recursion.
            capacity (int): The maximum allowed depth of recursion.
            msg_rest (list): The remaining message list to process.
            return_list (list): The list to append extracted submessages to.
        Returns:
            list: The list of extracted submessages.
        Raises:
            MessageWarningException: If the submessage type is unknown or if a submessage with structure type has a capacity other than 1.
        """
        
        if depth > capacity or len(msg_rest) == 0:
            return return_list

        logger.debug(f"Submessage raw: {list(map(lambda x: f'{x:<4}', msg_rest))}")
        logger.debug(f"Submessage hex: {list(map(lambda x: f'{hex(x):<4}', msg_rest))}")
        
        message_number = (msg_rest[0] << 8) | msg_rest[1]
        message_type = (message_number & 1536) >> 9
        logger.debug(f"Submessage number: {hex(message_number)}, Type: {message_type}")

        # Determine payload size based on type
        if message_type == 0:
            payload_size = 1
        elif message_type == 1:
            payload_size = 2
        elif message_type == 2:
            payload_size = 4
        elif message_type == 3:
            payload_size = len(msg_rest)
            if capacity != 1:
                raise MessageWarningException(argument=capacity, message="Submessage with structure type must have capacity of 1.")
        else:
            raise MessageWarningException(argument=message_type, message="Unknown Submessage type")
        
        payload = msg_rest[2:2 + payload_size]

        # Check if payload exceeds 255 characters
        if len(payload) > 255:
            logger.warning(f"Payload for Submessage {hex(message_number)} too large at index {depth}: {len(payload)} bytes. Truncating to 100 bytes.")
            payload = payload[:255]

        # convert the int list from payload to byteorder string
        logger.debug(f"Submessage Payload raw: {list(map(lambda x: f'{x:<4}', payload))}")
        logger.debug(f"Submessage Payload hex: {list(map(lambda x: f'{hex(x):<4}', payload))}")
        byte_string = bytes([int(hex(x), 16) for x in payload])
        logger.debug(f"Submessage Payload packed decimal: {byte_string}")
        return_list.append({"message_number": message_number, "message_type": message_type, "payload": byte_string})
        return self.extract_messages(depth + 1, capacity, msg_rest[2 + payload_size:], return_list)
    
    def determine_value(self, rawvalue, msgname):
        """
        Determines the processed value from a raw byte input based on the message name configuration.
        Args:
            rawvalue (bytes): The raw byte value to be processed.
            msgname (str): The name of the message which determines the processing rules.
        Returns:
            float or str: The processed value, which could be a numerical value or an enumerated string.
        Raises:
            Warning: Logs a warning if the arithmetic function cannot be applied and uses the raw value instead.
        """
        arithmetic = self.config.NASA_REPO[msgname]['arithmetic'].replace("value", 'packed_value')

        packed_value = int.from_bytes(rawvalue, byteorder='big', signed=True)

        if len(arithmetic) > 0:
            try:
                value = eval(arithmetic)
            except Exception as e:
                logger.warning(f"Arithmetic Function couldn't been applied, using raw value: arithmetic = {arithmetic} {e}")
                value = packed_value
        else:
            value = packed_value
        
        if self.config.NASA_REPO[msgname]['type'] == 'ENUM':
            if 'enum' in self.config.NASA_REPO[msgname]:
                value = self.config.NASA_REPO[msgname]['enum'][int.from_bytes(rawvalue, byteorder='big')]
            else:
                value = f"Unknown enum value: {value}"
        else:
            value = round(value, 3)
        return value
