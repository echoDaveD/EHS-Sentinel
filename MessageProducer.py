from CustomLogger import logger
from EHSArguments import EHSArguments
from EHSConfig import EHSConfig
from EHSExceptions import MessageWarningException
import asyncio

from NASAMessage import NASAMessage
from NASAPacket import NASAPacket, AddressClassEnum, PacketType, DataType

class MessageProducer:
    """
    The MessageProducer class is responsible for sending messages to the EHS-Sentinel system.
    It follows the singleton pattern to ensure only one instance is created. The class provides methods to request and write
    messages and transforme the value of message payloads based on predefined rules. It also includes logging for debugging and tracing the
    message producing steps.
    """

    _instance = None
    _CHUNKSIZE = 10 # message requests list will be split into this chunks, experience have shown that more then 10 are too much for an packet
    writer = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MessageProducer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, writer: asyncio.StreamWriter):
        if self._initialized:
            return
        self._initialized = True
        self.writer = writer
        self.config = EHSConfig()

    async def read_request(self, list_of_messages: list):
        chunks = [list_of_messages[i:i + self._CHUNKSIZE] for i in range(0, len(list_of_messages), self._CHUNKSIZE)]
        for chunk in chunks:
            await asyncio.sleep(0.5)
            nasa_packet = self._build_default_read_packet()
            nasa_packet.set_packet_messages([self._build_message(x) for x in chunk])
            await self._write_packet_to_serial(nasa_packet)

            if self.config.LOGGING['pollerMessage']:
                logger.info(f"Polling following NASAPacket: {nasa_packet}")
            else:
                logger.debug(f"Sent data NASAPacket: {nasa_packet}")

    async def write_request(self, message: str, value: str | int, read_request_after=False):
        nasa_packet = self._build_default_request_packet()
        nasa_packet.set_packet_messages([self._build_message(message.strip(), self._decode_value(message.strip(), value.strip()))])
        nasa_packet.to_raw()
        if self.config.LOGGING['controlMessage']:
            logger.info(f"Write request for {message} with value: {value}")
            logger.info(f"Sending NASA packet: {nasa_packet}")
        else:
            logger.debug(f"Write request for {message} with value: {value}")
            logger.debug(f"Sending NASA packet: {nasa_packet}")
        await self._write_packet_to_serial(nasa_packet)
        await asyncio.sleep(1)
        await self.read_request([message])      

    def _search_nasa_enumkey_for_value(self, message, value):
        if 'type' in self.config.NASA_REPO[message] and self.config.NASA_REPO[message]['type'] == 'ENUM':
            for key, val in self.config.NASA_REPO[message]['enum'].items():
                if val == value:
                    return key
                
        return None
    
    def is_number(self, s):
        return s.replace('+','',1).replace('-','',1).replace('.','',1).isdigit()

    def _decode_value(self, message, value) -> int:  
        enumval = self._search_nasa_enumkey_for_value(message, value)
        if enumval is None:
            if self.is_number(value):
                try:
                    value = int(value)
                except ValueError as e:
                    value = float(value)

                if 'reverse-arithmetic' in self.config.NASA_REPO[message]:
                    arithmetic = self.config.NASA_REPO[message]['reverse-arithmetic']
                else: 
                    arithmetic = ''
                if len(arithmetic) > 0:
                    try:
                        return int(eval(arithmetic))
                    except Exception as e:
                        logger.warning(f"Arithmetic Function couldn't been applied for Message {message}, using raw value: reverse-arithmetic = {arithmetic} {e} {value}")
                        return value
        else:
            value = int(enumval)

        return value

    def _build_message(self, message, value=None) -> NASAMessage:
        tmpmsg = NASAMessage()
        tmpmsg.set_packet_message(self._extract_address(message))
        if value is None:
            value = 0
        if tmpmsg.packet_message_type == 0:
            value_raw = value.to_bytes(1, byteorder='big', signed=True) 
        elif tmpmsg.packet_message_type == 1:
            value_raw = value.to_bytes(2, byteorder='big', signed=True) 
        elif tmpmsg.packet_message_type == 2:
            value_raw = value.to_bytes(4, byteorder='big', signed=True) 
        else:
            raise MessageWarningException(argument=tmpmsg.packet_message_type, message=f"Unknown Type for {message} type:")
        tmpmsg.set_packet_payload_raw(value_raw)
        return tmpmsg

    def _extract_address(self, messagename) -> int:
        return int(self.config.NASA_REPO[messagename]['address'], 16)

    def _build_default_read_packet(self) -> NASAPacket:
        nasa_msg = NASAPacket()
        nasa_msg.set_packet_source_address_class(AddressClassEnum.JIGTester)
        nasa_msg.set_packet_source_channel(255)
        nasa_msg.set_packet_source_address(0)
        nasa_msg.set_packet_dest_address_class(AddressClassEnum.BroadcastSetLayer)
        nasa_msg.set_packet_dest_channel(0)
        nasa_msg.set_packet_dest_address(32)
        nasa_msg.set_packet_information(True)
        nasa_msg.set_packet_version(2)
        nasa_msg.set_packet_retry_count(0)
        nasa_msg.set_packet_type(PacketType.Normal)
        nasa_msg.set_packet_data_type(DataType.Read)
        nasa_msg.set_packet_number(166)
        return nasa_msg
    
    def _build_default_request_packet(self) -> NASAPacket:
        nasa_msg = NASAPacket()
        nasa_msg.set_packet_source_address_class(AddressClassEnum.JIGTester)
        nasa_msg.set_packet_source_channel(0)
        nasa_msg.set_packet_source_address(255)
        nasa_msg.set_packet_dest_address_class(AddressClassEnum.Indoor)
        nasa_msg.set_packet_dest_channel(0)
        nasa_msg.set_packet_dest_address(0)
        nasa_msg.set_packet_information(True)
        nasa_msg.set_packet_version(2)
        nasa_msg.set_packet_retry_count(0)
        nasa_msg.set_packet_type(PacketType.Normal)
        nasa_msg.set_packet_data_type(DataType.Request)
        nasa_msg.set_packet_number(166)
        return nasa_msg

    async def _write_packet_to_serial(self, packet: NASAPacket):
        final_packet = packet.to_raw()
        self.writer.write(final_packet)
        await self.writer.drain()
    