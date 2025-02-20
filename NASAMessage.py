
class NASAMessage:
    """
    A class to represent a NASA message.
    Attributes
    ----------
    packet_message : int
        The message packet identifier.
    packet_message_type : int
        The type of the message packet.
    packet_payload : bytes
        The payload of the message packet in bytes.
    Methods
    -------
    __str__():
        Returns a string representation of the NASAMessage instance.
    __repr__():
        Returns a string representation of the NASAMessage instance.
    """
    def __init__(self, packet_message=0x000, packet_message_type=0, packet_payload=[0]):
        """
        Constructs all the necessary attributes for the NASAMessage object.
        Parameters
        ----------
        packet_message : int, optional
            The message packet identifier (default is 0x000).
        packet_message_type : int, optional
            The type of the message packet (default is 0).
        packet_payload : list, optional
            The payload of the message packet as a list of integers (default is [0]).
        """
        """
        Returns a string representation of the NASAMessage instance.
        Returns
        -------
        str
            A string representation of the NASAMessage instance.
        """
        """
        Returns a string representation of the NASAMessage instance.
        Returns
        -------
        str
            A string representation of the NASAMessage instance.
        """
        
        self.packet_message: int = packet_message
        self.packet_message_type: int = packet_message_type
        self.packet_payload: bytes = bytes([int(hex(x), 16) for x in packet_payload])


    def set_packet_message(self, value: int):
        self.packet_message = value

    def set_packet_message_type(self, value: int):
        self.packet_message_type = value

    def set_packet_payload(self, value: list):
        self.packet_payload = bytes([int(hex(x), 16) for x in value])

    def to_raw(self) -> bytearray:

        message_number_reconstructed = (self.packet_message_type << 9) | (self.packet_message & 0x1FF)

        # Extract the original bytes from message_number
        msg_rest_0 = (self.packet_message >> 8) & 0xFF  # Upper 8 bits
        msg_rest_1 = self.packet_message & 0xFF          # Lower 8 bits
        msgpayload = int.from_bytes(self.packet_payload, byteorder='big', signed=True)
        if self.packet_message_type == 0:
            return [
                msg_rest_0,
                msg_rest_1,
                msgpayload & 0xFF
            ]
        elif self.packet_message_type == 1:
            return [
                msg_rest_0,
                msg_rest_1,
                (msgpayload >> 8) & 0xFF,
                msgpayload & 0xFF 
            ]
        elif self.packet_message_type == 2:
            return [
                msg_rest_0,
                msg_rest_1,
                (msgpayload >> 24) & 0xFF,
                (msgpayload >> 16) & 0xFF,
                (msgpayload >> 8) & 0xFF,
                msgpayload & 0xFF
            ]

    def __str__(self):
        return (
            f"NASAMessage(\n"
            f"    packet_message={self.packet_message} ({hex(self.packet_message)}) ({[x for x in bytearray(self.packet_message.to_bytes(2))]}),\n"
            f"    packet_message_type={self.packet_message_type} ({hex(self.packet_message_type)}),\n"
            f"    packet_payload={self.packet_payload} ({self.packet_payload.hex()}) ({[int(x) for x in self.packet_payload]})\n"
            f")"
        )
    
    def __repr__(self):
        return self.__str__()