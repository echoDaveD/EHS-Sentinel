from enum import Enum
from NASAMessage import NASAMessage
from EHSExceptions import SkipInvalidPacketException
import binascii

class AddressClassEnum(Enum):
    """
    Enum class representing various address classes for NASA packets.
    Attributes:
        Outdoor (int): Address class for outdoor units (0x10).
        HTU (int): Address class for HTU units (0x11).
        Indoor (int): Address class for indoor units (0x20).
        ERV (int): Address class for ERV units (0x30).
        Diffuser (int): Address class for diffuser units (0x35).
        MCU (int): Address class for MCU units (0x38).
        RMC (int): Address class for RMC units (0x40).
        WiredRemote (int): Address class for wired remote units (0x50).
        PIM (int): Address class for PIM units (0x58).
        SIM (int): Address class for SIM units (0x59).
        Peak (int): Address class for peak units (0x5A).
        PowerDivider (int): Address class for power divider units (0x5B).
        OnOffController (int): Address class for on/off controller units (0x60).
        WiFiKit (int): Address class for WiFi kit units (0x62).
        CentralController (int): Address class for central controller units (0x65).
        DMS (int): Address class for DMS units (0x6A).
        JIGTester (int): Address class for JIG tester units (0x80).
        BroadcastSelfLayer (int): Address class for broadcast self layer (0xB0).
        BroadcastControlLayer (int): Address class for broadcast control layer (0xB1).
        BroadcastSetLayer (int): Address class for broadcast set layer (0xB2).
        BroadcastCS (int): Address class for broadcast CS (0xB3).
        BroadcastControlAndSetLayer (int): Address class for broadcast control and set layer (0xB3).
        BroadcastModuleLayer (int): Address class for broadcast module layer (0xB4).
        BroadcastCSM (int): Address class for broadcast CSM (0xB7).
        BroadcastLocalLayer (int): Address class for broadcast local layer (0xB8).
        BroadcastCSML (int): Address class for broadcast CSML (0xBF).
        Undefined (int): Address class for undefined units (0xFF).
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

class PacketType(Enum):
    """
    Enum class representing different types of packets in the EHS-Sentinel system.
    Attributes:
        StandBy (int): Represents a standby packet type with a value of 0.
        Normal (int): Represents a normal packet type with a value of 1.
        Gathering (int): Represents a gathering packet type with a value of 2.
        Install (int): Represents an install packet type with a value of 3.
        Download (int): Represents a download packet type with a value of 4.
    """

    StandBy = 0
    Normal = 1
    Gathering = 2
    Install = 3
    Download = 4

class DataType(Enum):
    """
    Enum representing different types of data operations.
    Attributes:
        Undefined (int): Represents an undefined data type (0).
        Read (int): Represents a read operation (1).
        Write (int): Represents a write operation (2).
        Request (int): Represents a request operation (3).
        Notification (int): Represents a notification operation (4).
        Response (int): Represents a response operation (5).
        Ack (int): Represents an acknowledgment (6).
        Nack (int): Represents a negative acknowledgment (7).
    """

    Undefined = 0
    Read = 1
    Write = 2
    Request = 3
    Notification = 4
    Resposne = 5
    Ack = 6
    Nack = 7

class NASAPacket:
    """
    A class to represent a NASA Packet.
    Attributes
    ----------
    _packet_raw : bytearray
        Raw packet data.
    packet_start : int
        Start byte of the packet.
    packet_size : int
        Size of the packet.
    packet_source_address_class : AddressClassEnum
        Source address class of the packet.
    packet_source_channel : int
        Source channel of the packet.
    packet_source_address : int
        Source address of the packet.
    packet_dest_address_class : AddressClassEnum
        Destination address class of the packet.
    packet_dest_channel : int
        Destination channel of the packet.
    packet_dest_address : int
        Destination address of the packet.
    packet_information : int
        Information field of the packet.
    packet_version : int
        Version of the packet.
    packet_retry_count : int
        Retry count of the packet.
    packet_type : PacketType
        Type of the packet.
    packet_data_type : DataType
        Data type of the packet.
    packet_number : int
        Number of the packet.
    packet_capacity : int
        Capacity of the packet.
    packet_messages : list[NASAMessage]
        List of messages in the packet.
    packet_crc16 : int
        CRC16 checksum of the packet.
    packet_end : int
        End byte of the packet.
    Methods
    -------
    parse(packet: bytearray):
        Parses the given packet data.
    _extract_messages(depth: int, capacity: int, msg_rest: bytearray, return_list: list):
        Recursively extracts messages from the packet.
    __str__():
        Returns a string representation of the NASAPacket.
    __repr__():
        Returns a string representation of the NASAPacket.
    """

    def __init__(self):
        self._packet_raw: bytearray = None
        self.packet_start: int = None
        self.packet_size: int = None
        self.packet_source_address_class: AddressClassEnum = None
        self.packet_source_channel: int = None
        self.packet_source_address: int = None
        self.packet_dest_address_class: AddressClassEnum = None
        self.packet_dest_channel: int = None
        self.packet_dest_address: int = None
        self.packet_information: int = None
        self.packet_version: int = None
        self.packet_retry_count: int = None
        self.packet_type: PacketType = None
        self.packet_data_type: DataType = None
        self.packet_number: int = None
        self.packet_capacity: int = None
        self.packet_messages: list[NASAMessage] = None
        self.packet_crc16: int = None
        self.packet_end: int = None

    def parse(self, packet: bytearray):
        """
        Parses a given bytearray packet and extracts various fields into the object's attributes.
        Args:
            packet (bytearray): The packet to be parsed.
        Raises:
            ValueError: If the packet length is less than 14 bytes.
        Attributes:
            packet_start (int): The start byte of the packet.
            packet_size (int): The size of the packet.
            packet_source_address_class (AddressClassEnum): The source address class of the packet.
            packet_source_channel (int): The source channel of the packet.
            packet_source_address (int): The source address of the packet.
            packet_dest_address_class (AddressClassEnum): The destination address class of the packet.
            packet_dest_channel (int): The destination channel of the packet.
            packet_dest_address (int): The destination address of the packet.
            packet_information (bool): Information flag of the packet.
            packet_version (int): Version of the packet.
            packet_retry_count (int): Retry count of the packet.
            packet_type (PacketType): Type of the packet.
            packet_data_type (DataType): Data type of the packet.
            packet_number (int): Number of the packet.
            packet_capacity (int): Capacity of the packet.
            packet_crc16 (int): CRC16 checksum of the packet.
            packet_end (int): The end byte of the packet.
            packet_messages (list): Extracted messages from the packet.
        """

        self._packet_raw = packet
        if len(packet) < 14:
            raise ValueError("Data too short to be a valid NASAPacket")
        
        crc_checkusm=binascii.crc_hqx(bytearray(packet[3:-3]), 0)

        self.packet_start = packet[0]
        self.packet_size = ((packet[1] << 8) | packet[2])
        try:
            self.packet_source_address_class = AddressClassEnum(packet[3])
        except ValueError as e:
            raise SkipInvalidPacketException(f"Source Adress Class out of enum {packet[3]}")
        self.packet_source_channel = packet[4]
        self.packet_source_address = packet[5]
        try:
            self.packet_dest_address_class = AddressClassEnum(packet[6])
        except ValueError as e:
            raise SkipInvalidPacketException(f"Destination Adress Class out of enum {packet[6]}")
        self.packet_dest_channel = packet[7]
        self.packet_dest_address = packet[8]
        self.packet_information = (int(packet[9]) & 128) >> 7 == 1
        self.packet_version = (int(packet[9]) & 96) >> 5
        self.packet_retry_count = (int(packet[9]) & 24) >> 3
        self.packet_type = PacketType((int(packet[10]) & 240) >> 4)
        self.packet_data_type = DataType(int(packet[10]) & 15)
        self.packet_number = packet[11]
        self.packet_capacity = packet[12]
        self.packet_crc16 = ((packet[-3] << 8) | packet[-2]) # + 2
        self.packet_end = packet[-1]
        self.packet_messages = self._extract_messages(0, self.packet_capacity, packet[13:-3], [])

        if crc_checkusm != self.packet_crc16:
            raise SkipInvalidPacketException(f"Checksum for package could not be validatet calculated: {crc_checkusm} in packet: {self.packet_crc16}: packet:{self}")

    def _extract_messages(self, depth: int, capacity: int, msg_rest: bytearray, return_list: list):
        """
        Recursively extracts messages from a bytearray and appends them to a list.
        Args:
            depth (int): The current depth of recursion.
            capacity (int): The maximum allowed depth of recursion.
            msg_rest (bytearray): The remaining bytes to be processed.
            return_list (list): The list to which extracted messages are appended.
        Returns:
            list: The list of extracted messages.
        Raises:
            ValueError: If the message type is unknown, the capacity is invalid for a structure type message,
                or the payload size exceeds 255 bytes.
        """

        if depth > capacity or len(msg_rest) <= 2:
            return return_list
        
        message_number = (msg_rest[0] << 8) | msg_rest[1]
        message_type = (message_number & 1536) >> 9

        if message_type == 0:
            payload_size = 1
        elif message_type == 1:
            payload_size = 2
        elif message_type == 2:
            payload_size = 4
        elif message_type == 3:
            payload_size = len(msg_rest)
            if capacity != 1:
                raise SkipInvalidPacketException("Message with structure type must have capacity of 1.")
        else:
            raise ValueError(f"Mssage type unknown: {message_type}")
        
        payload = msg_rest[2:2 + payload_size]
        if len(payload) > 255:
            raise ValueError(f"Payload for Submessage {hex(message_number)} too large at index {depth}: {len(payload)} bytes.")
        
        return_list.append(NASAMessage(packet_message=message_number, packet_message_type=message_type, packet_payload=payload))
        return self._extract_messages(depth+1, capacity, msg_rest[2 + payload_size:], return_list)

    def __str__(self):
        text =  f"NASAPacket(\n"
        text += f"    start={self.packet_start} ({hex(self.packet_start)}),\n"
        text += f"    size={self.packet_size} ({hex(self.packet_size)}),\n"
        text += f"    source_address_class={self.packet_source_address_class} ({hex(self.packet_source_address_class.value)}),\n"
        text += f"    source_channel={self.packet_source_channel} ({hex(self.packet_source_channel)}),\n"
        text += f"    source_address={self.packet_source_address} ({hex(self.packet_source_address)}),\n"
        text += f"    dest_address_class={self.packet_dest_address_class} ({hex(self.packet_dest_address_class.value)}),\n"
        text += f"    dest_channel={self.packet_dest_channel} ({hex(self.packet_dest_channel)}),\n"
        text += f"    dest_address={self.packet_dest_address} ({hex(self.packet_dest_address)}),\n"
        text += f"    information={self.packet_information},\n"
        text += f"    version={self.packet_version} ({hex(self.packet_version)}),\n"
        text += f"    retry_count={self.packet_retry_count} ({hex(self.packet_retry_count)}),\n"
        text += f"    type={self.packet_type} ({hex(self.packet_type.value)}),\n"
        text += f"    data_type={self.packet_data_type} ({hex(self.packet_data_type.value)}),\n"
        text += f"    number={self.packet_number} ({hex(self.packet_number)}),\n"
        text += f"    capacity={self.packet_capacity} ({hex(self.packet_capacity)}),\n"
        text += f"    messages=[\n"
        for msg in self.packet_messages:
            lines = f"{msg}".splitlines()
            text += f"        {lines[0]}\n"
            for line in lines[1:-1]:
                text += f"            {line}\n"
            text += f"        {lines[-1]}\n"
        text +=  "    ],\n"
        text += f"    crc16={self.packet_crc16} ({hex(self.packet_crc16)}),\n"
        text += f"    end={self.packet_end} ({hex(self.packet_end)})\n"
        text += f")"
        return text

    def __repr__(self):
        return self.__str__()
    

    # Setter methods
    def set_packet_source_address_class(self, value: AddressClassEnum):
        self.packet_source_address_class = value

    def set_packet_source_channel(self, value: int):
        self.packet_source_channel = value

    def set_packet_source_address(self, value: int):
        self.packet_source_address = value

    def set_packet_dest_address_class(self, value: AddressClassEnum):
        self.packet_dest_address_class = value

    def set_packet_dest_channel(self, value: int):
        self.packet_dest_channel = value

    def set_packet_dest_address(self, value: int):
        self.packet_dest_address = value

    def set_packet_information(self, value: bool):
        self.packet_information = value

    def set_packet_version(self, value: int):
        self.packet_version = value

    def set_packet_retry_count(self, value: int):
        self.packet_retry_count = value

    def set_packet_type(self, value: PacketType):
        self.packet_type = value

    def set_packet_data_type(self, value: DataType):
        self.packet_data_type = value

    def set_packet_number(self, value: int):
        self.packet_number = value

    def set_packet_capacity(self, value: int):
        self.packet_capacity = value

    def set_packet_messages(self, value: list[NASAMessage]):
        self.packet_messages = value

    def to_raw(self) -> bytearray:
        """
        Converts the NASAPacket object back to its raw byte representation.
        Returns:
            bytearray: The raw byte representation of the packet.
        """
        packet = bytearray(14 + len(self.packet_messages) * 2)  # Adjust size as needed
        packet[0] = 0x32
        packet[1] = (self.packet_size >> 8) & 0xFF
        packet[2] = self.packet_size & 0xFF
        packet[3] = self.packet_source_address_class.value
        packet[4] = self.packet_source_channel
        packet[5] = self.packet_source_address
        packet[6] = self.packet_dest_address_class.value
        packet[7] = self.packet_dest_channel
        packet[8] = self.packet_dest_address
        packet[9] = (self.packet_information << 7) | (self.packet_version << 5) | (self.packet_retry_count << 3)
        packet[10] = (self.packet_type.value << 4) | self.packet_data_type.value
        packet[11] = self.packet_number
        packet[12] = self.packet_capacity
        # Add messages to the packet
        index = 13
        for msg in self.packet_messages:
            packet[index:index + 2] = msg.to_bytes()
            index += 2
        packet[-3] = (self.packet_crc16 >> 8) & 0xFF
        packet[-2] = self.packet_crc16 & 0xFF
        packet[-1] = 0x34
        #crc=binascii.crc_hqx(packet, 0)
        #final_packet = struct.pack(">BH", 0x32, len(packet)+2+2) + packet + struct.pack(">HB", crc, 0x34)
        return packet

# Example usage:
# packet = NASAPacket()
# packet.parse(bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06]))
# print(packet)