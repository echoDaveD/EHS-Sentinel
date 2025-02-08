
import struct
import binascii

from NASAMessage import NASAMessage
from NASAPacket import NASAPacket
print(NASAMessage(packet_message=0x9999, packet_message_type=1))
#[0x32, 0x0, 0x16, 0x10, 0x0, 0x0, 0xb0, 0x0, 0xff, 0xc0, 0x14, 0x8b, 0x2, 0x82, 0x37, 0x0, 0x20, 0x82, 0x38, 0x0, 0x23, 0xb8, 0xce, 0x34]
#[0x32, 0x0, 0x16, 0x10, 0x0, 0x0, 0xb0, 0x0, 0xff, 0xc0, 0x14, 0x8b, 0x2, 0x82, 0x37, 0x0, 0x20, 0x82, 0x38, 0x0, 0x23, 0xb8, 0xce, 0x34]
packet = bytearray([0x10, 0x0, 0x0, 0xb0, 0x0, 0xff, 0xc0, 0x14, 0x8b, 0x2, 0x82, 0x37, 0x0, 0x20, 0x82, 0x38, 0x0, 0x23])
crc=binascii.crc_hqx(packet, 0)
# NOTE: include length of CRC(2) and length of length field(2) in the 
#       total length, exclude SF/TF of total length 
final_packet = struct.pack(">BH", 0x32, len(packet)+2+2) + packet + struct.pack(">HB", crc, 0x34)
tst = bytearray([0x32, 0x0, 0x16, 0x10, 0x0, 0x0, 0xb0, 0x0, 0xff, 0xc0, 0x14, 0x8b, 0x2, 0x82, 0x37, 0x0, 0x20, 0x82, 0x38, 0x0, 0x23, 0xb8, 0xce, 0x34])
test = NASAPacket()
test.parse(tst)
print(test)

print(f"Sent data raw: {[hex(x) for x in final_packet]}")

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

test = NASAPacket()
test.parse(final_packet)
print(test)

print([hex(x) for x in final_packet])