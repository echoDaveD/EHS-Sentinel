import asyncio
import logging
import traceback
import yaml
from CustomLogger import logger
from EHSArguments import EHSArguments
from EHSConfig import EHSConfig
from EHSExceptions import MessageWarningException
from MQTTClient import MQTTClient

from NASAMessage import NASAMessage
from NASAPacket import NASAPacket

class MessageProcessor:
    """
    The MessageProcessor class is responsible for handling and processing incoming messages for the EHS-Sentinel system.
    The class provides methods to process messages, extract submessages, search for message definitions in a configuration repository, 
    and determine the value of message payloads based on predefined rules. It also includes logging for debugging and tracing the
    message processing steps.
    """

    def __init__(self):
        self._initialized = True
        self.config = EHSConfig()
        self.args = EHSArguments()
        self.mqtt = MQTTClient()

    async def process_message(self, packet: NASAPacket):
        for msg in packet.packet_messages:
            hexmsg = f"0x{msg.packet_message:04x}" #hex(msg.packet_message)
            msgname = self.search_nasa_table(hexmsg)
            if msgname is not None:
                try:
                    msgvalue = self.determine_value(msg.packet_payload, msgname, msg.packet_message_type)
                except Exception as e:
                    raise MessageWarningException(argument=f"{msg.packet_payload}/{[hex(x) for x in msg.packet_payload]}", message=f"Value of {hexmsg} couldn't be determinate, skip Message {e}")
                await self.protocolMessage(msg, msgname, msgvalue)
            else:
                packedval = int.from_bytes(msg.packet_payload, byteorder='big', signed=True)
                if self.config.LOGGING['messageNotFound']:
                    logger.info(f"Message not Found in NASA repository: {hexmsg:<6} Type: {msg.packet_message_type} Payload: {msg.packet_payload} = {packedval}")
                else:
                    logger.debug(f"Message not Found in NASA repository: {hexmsg:<6} Type: {msg.packet_message_type} Payload: {msg.packet_payload} = {packedval}")

    async def protocolMessage(self, msg: NASAMessage, msgname, msgvalue):

        if self.config.LOGGING['proccessedMessage']:
            logger.info(f"Message number: {hex(msg.packet_message):<6} {msgname:<50} Type: {msg.packet_message_type} Payload: {msgvalue} ({msg.packet_payload})")
        else:
            logger.debug(f"Message number: {hex(msg.packet_message):<6} {msgname:<50} Type: {msg.packet_message_type} Payload: {msgvalue}")

        if self.config.GENERAL['protocolFile'] is not None:
            with open(self.config.GENERAL['protocolFile'], "a") as protWriter:
                protWriter.write(f"{hex(msg.packet_message):<6},{msg.packet_message_type},{msgname:<50},{msgvalue}\n")

        await self.mqtt.publish_message(msgname, msgvalue)

        self.config.NASA_VAL_STORE[msgname] = msgvalue

        if msgname in ['NASA_OUTDOOR_TW2_TEMP', 'NASA_OUTDOOR_TW1_TEMP', 'VAR_IN_FLOW_SENSOR_CALC']:
            if all(k in self.config.NASA_VAL_STORE for k in ['NASA_OUTDOOR_TW2_TEMP', 'NASA_OUTDOOR_TW1_TEMP', 'VAR_IN_FLOW_SENSOR_CALC']):
                value = round(
                    abs(
                        (self.config.NASA_VAL_STORE['NASA_OUTDOOR_TW2_TEMP'] - self.config.NASA_VAL_STORE['NASA_OUTDOOR_TW1_TEMP']) * 
                        (self.config.NASA_VAL_STORE['VAR_IN_FLOW_SENSOR_CALC']/60) 
                        * 4190
                    ) , 4
                )
                if (value < 15000 and value > 0): # only if heater output between 0 und 15000 W
                    await self.protocolMessage(NASAMessage(packet_message=0x9999, packet_message_type=1, packet_payload=[0]),
                                        "NASA_EHSSENTINEL_HEAT_OUTPUT", 
                                        value
                                        )

        if msgname in ('NASA_EHSSENTINEL_HEAT_OUTPUT', 'NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT'):
            if all(k in self.config.NASA_VAL_STORE for k in ['NASA_EHSSENTINEL_HEAT_OUTPUT', 'NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT']):
                if (self.config.NASA_VAL_STORE['NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT'] > 0):
                    value = round((self.config.NASA_VAL_STORE['NASA_EHSSENTINEL_HEAT_OUTPUT'] / self.config.NASA_VAL_STORE['NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT']/1000.), 3)
                    if (value < 20 and value > 0):
                        await self.protocolMessage(NASAMessage(packet_message=0x9998, packet_message_type=1, packet_payload=[0]), 
                                                "NASA_EHSSENTINEL_COP",
                                                value
                                                )
                    
        if msgname in ('NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT_ACCUM', 'LVAR_IN_TOTAL_GENERATED_POWER'):
            if all(k in self.config.NASA_VAL_STORE for k in ['NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT_ACCUM', 'LVAR_IN_TOTAL_GENERATED_POWER']):
                if (self.config.NASA_VAL_STORE['NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT_ACCUM'] > 0):
                    value = round(self.config.NASA_VAL_STORE['LVAR_IN_TOTAL_GENERATED_POWER'] / self.config.NASA_VAL_STORE['NASA_OUTDOOR_CONTROL_WATTMETER_ALL_UNIT_ACCUM'], 3)

                    if (value < 20 and value > 0):
                        await self.protocolMessage(NASAMessage(packet_message=0x9997, packet_message_type=1, packet_payload=[0]), 
                                                "NASA_EHSSENTINEL_TOTAL_COP",
                                                value
                                                )

    def search_nasa_table(self, address):
        for key, value in self.config.NASA_REPO.items():
            if value['address'].lower() == address:
                return key
            
    def is_valid_rawvalue(self, rawvalue: bytes) -> bool:
        return all(0x20 <= b <= 0x7E or b in (0x00, 0xFF) for b in rawvalue)

    def determine_value(self, rawvalue, msgname, packet_message_type):
        if packet_message_type == 3:
            value = ""

            if self.is_valid_rawvalue(rawvalue[1:-1]):
                for byte in rawvalue[1:-1]:
                    if byte != 0x00 and byte != 0xFF:
                        char = chr(byte) if 32 <= byte <= 126 else f"{byte}"
                        value += char
                    else:
                        value += " "
                value = value.strip()
            else:
                value = "".join([f"{int(x)}" for x in rawvalue])
            
            #logger.info(f"{msgname} Structure: {rawvalue} type of {value}")
        else:
            if 'arithmetic' in self.config.NASA_REPO[msgname]:
                arithmetic = self.config.NASA_REPO[msgname]['arithmetic'].replace("value", 'packed_value')
            else: 
                arithmetic = ''

            packed_value = int.from_bytes(rawvalue, byteorder='big', signed=True)

            if len(arithmetic) > 0:
                try:
                    value = eval(arithmetic)
                except Exception as e:
                    logger.warning(f"Arithmetic Function couldn't been applied for Message {msgname}, using raw value: arithmetic = {arithmetic} {e} {packed_value} {rawvalue}")
                    value = packed_value
            else:
                value = packed_value

            value = round(value, 3)

            if 'type' in self.config.NASA_REPO[msgname]:
                if self.config.NASA_REPO[msgname]['type'] == 'ENUM':
                    if 'enum' in self.config.NASA_REPO[msgname]:
                        value = self.config.NASA_REPO[msgname]['enum'][int.from_bytes(rawvalue, byteorder='big')]
                    else:
                        value = f"Unknown enum value: {value}"
                
        return value
