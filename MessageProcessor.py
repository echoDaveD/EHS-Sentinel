import asyncio
import logging
import traceback
import yaml
from CustomLogger import logger, setSilent
from EHSArguments import EHSArguments
from EHSConfig import EHSConfig
from EHSExceptions import MessageWarningException
from MQTTClient import MQTTClient

from NASAMessage import NASAMessage
from NASAPacket import NASAPacket

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
        self.mqtt = MQTTClient()
        self.NASA_VAL_STORE = {}

    def process_message(self, packet: NASAPacket):
        """
        Processes an incoming packet .
        Args:
            message (list): A list of integers representing the message bytes.
        Raises:
            MessageWarningException: If the message is invalid due to missing end byte, incorrect length, or other processing errors.
        Logs:
            Various debug and info logs to trace the processing steps, including packet size, raw and hex message content, source address, capacity, and extracted message details.
        """
        for msg in packet.packet_messages:
            hexmsg = hex(msg.packet_message)
            msgname = self.search_nasa_table(hexmsg)
            if msgname is not None:
                try:
                    msgvalue = self.determine_value(msg.packet_payload, msgname)
                except Exception as e:
                    raise MessageWarningException(argument=f"{msg.packet_payload}/{[hex(x) for x in msg.packet_payload]}", message=f"Value of {hexmsg} couldn't be determinate, skip Message {e}")
                self.protocolMessage(msg, msgname, msgvalue)
            else:
                logger.debug(f"Message not Found in NASA repository: {hexmsg:<6} Type: {msg.packet_message_type} Payload: {msg.packet_payload}")

    def protocolMessage(self, msg: NASAMessage, msgname, msgvalue):
        """
        Processes a protocol message by logging, writing to a protocol file, publishing via MQTT, 
        and updating internal value store. Additionally, it calculates and processes specific 
        derived values based on certain message names.
        Args:
            msg (NASAMessage): The NASA message object containing packet information.
            msgname (str): The name of the message.
            msgvalue (Any): The value of the message.
        Side Effects:
            - Logs the message details.
            - Appends the message details to a protocol file if configured.
            - Publishes the message via MQTT.
            - Updates the internal NASA value store with the message value.
            - Calculates and processes derived values for specific message names.
        """

        logger.info(f"Message number: {hex(msg.packet_message):<6} {msgname:<50} Type: {msg.packet_message_type} Payload: {msgvalue}")

        if self.config.GENERAL['protocolFile'] is not None:
            with open(self.config.GENERAL['protocolFile'], "a") as protWriter:
                protWriter.write(f"{hex(msg.packet_message):<6},{msg.packet_message_type},{msgname:<50},{msgvalue}\n")

        self.mqtt.publish_message(msgname, msgvalue)

        self.NASA_VAL_STORE[msgname] = msgvalue

        if msgname in ['NASA_OUTDOOR_TW2_TEMP', 'NASA_OUTDOOR_TW1_TEMP', 'VAR_IN_FLOW_SENSOR_CALC']:
            if all(k in self.NASA_VAL_STORE for k in ['NASA_OUTDOOR_TW2_TEMP', 'NASA_OUTDOOR_TW1_TEMP', 'VAR_IN_FLOW_SENSOR_CALC']):
                self.protocolMessage(NASAMessage(packet_message=0x9999, packet_message_type=1),
                                    "NASA_EHSSENTINEL_HEAT_OUTPUT", 
                                    round(
                                            (
                                                (self.NASA_VAL_STORE['NASA_OUTDOOR_TW2_TEMP'] - self.NASA_VAL_STORE['NASA_OUTDOOR_TW1_TEMP']) * 
                                                (self.NASA_VAL_STORE['VAR_IN_FLOW_SENSOR_CALC']/60) 
                                                * 4190
                                            ), 4))

        if msgname in ('NASA_EHSSENTINEL_HEAT_OUTPUT', 'NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT'):
            if all(k in self.NASA_VAL_STORE for k in ['NASA_EHSSENTINEL_HEAT_OUTPUT', 'NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT']):
                if (self.NASA_VAL_STORE['NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT'] > 0):
                    self.protocolMessage(NASAMessage(packet_message=0x9998, packet_message_type=1), 
                                            "NASA_EHSSENTINEL_COP",
                                            round((self.NASA_VAL_STORE['NASA_EHSSENTINEL_HEAT_OUTPUT'] / self.NASA_VAL_STORE['NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT']/1000.), 3))

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
                value = self.config.NASA_REPO[msgname]['enum'][int.from_bytes(rawvalue, byteorder='big')].upper()
            else:
                value = f"Unknown enum value: {value}"
        else:
            value = round(value, 3)
        return value
