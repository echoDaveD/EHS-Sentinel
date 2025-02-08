
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

    def __str__(self):
        return (
            f"NASAMessage(\n"
            f"    packet_message={self.packet_message} ({hex(self.packet_message)}),\n"
            f"    packet_message_type={self.packet_message_type} ({hex(self.packet_message_type)}),\n"
            f"    packet_payload={self.packet_payload} ({self.packet_payload.hex()})\n"
            f")"
        )
    
    def __repr__(self):
        return self.__str__()