import os
import sys
import inspect
import asyncio
import yaml
import traceback
import pprint

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

from NASAPacket import NASAPacket, AddressClassEnum, DataType, PacketType
from NASAMessage import NASAMessage

# Generate a list of all possible 2-byte hex values, always padded to 4 characters
found_repo = {}

with open('data/NasaRepository.yml', mode='r') as file:
    NASA_REPO = yaml.safe_load(file)

async def main():

    # load finder file and anylse it
    with open('helpertils/messagesFound.txt', mode='r') as file:
        lines = file.read()
        for line in lines.splitlines():
            nix, nr, msgnr, msgname, type, packedval, rawval, nix2 = line.split("|")
            if type.strip() != '3':
                packedval = int(packedval.strip())
            if len(msgname.strip()) == 0 and packedval != -1:
                found_repo[msgnr.strip()] = {
                    "type": type.strip(),
                    "raw_value": rawval.strip(),
                    "packed_value": packedval
                }
    
    pprint.pprint(found_repo)

    # load config
    with open('config.yml', mode='r') as file:
            config = yaml.safe_load(file)

    # Print the total count to confirm all values are included
    print(f"Total values: {len(found_repo)}")

    reader, writer = await asyncio.open_connection('172.19.2.240', 4196)
    print(" serial_connection fertig")
    await asyncio.gather(
        serial_read(reader, config),
        serial_write(writer, config),
    )

async def serial_write(writer: asyncio.StreamWriter, config):
    _CHUNKSIZE=10
    keys = list(found_repo.keys())
    chunks = [keys[i:i + _CHUNKSIZE] for i in range(0, len(keys), _CHUNKSIZE)]
    while True:
        print("Start Writing")
        for chunk in chunks:
            nasa_msg = NASAPacket()
            nasa_msg.set_packet_source_address_class(AddressClassEnum.JIGTester)
            nasa_msg.set_packet_source_channel(240)
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
            msglist=[]
            for msg in chunk:
                tmpmsg = NASAMessage()
                tmpmsg.set_packet_message(int(msg, 16))
                value = 0
                if tmpmsg.packet_message_type == 0:
                    value_raw = value.to_bytes(1, byteorder='big') 
                elif tmpmsg.packet_message_type == 1:
                    value_raw = value.to_bytes(2, byteorder='big') 
                elif tmpmsg.packet_message_type == 2:
                    value_raw = value.to_bytes(4, byteorder='big') 
                else:
                    value_raw = value.to_bytes(1, byteorder='big') 

                tmpmsg.set_packet_payload_raw(value_raw)
                msglist.append(tmpmsg)
            nasa_msg.set_packet_messages(msglist)
            raw = nasa_msg.to_raw()
            writer.write(raw)
            await writer.drain()
            await asyncio.sleep(1)
        print("End Writing")
        await asyncio.sleep(120)

async def serial_read(reader: asyncio.StreamReader, config):
    prev_byte = 0x00
    packet_started = False
    data = bytearray()
    packet_size = 0

    while True:
        current_byte = await reader.read(1)  # read bitewise
        
        #data = await reader.read(1024)
        #data = await reader.readuntil(b'\x34fd')
        if current_byte:
            if packet_started:
                data.extend(current_byte)
                if len(data) == 3:
                    packet_size = ((data[1] << 8) | data[2]) + 2
    
                if packet_size <= len(data):
                    asyncio.create_task(process_packet(data, config))
                    data = bytearray()
                    packet_started = False

            # identify packet start
            if current_byte == b'\x00' and prev_byte == b'\x32':
                packet_started = True
                data.extend(prev_byte)
                data.extend(current_byte)

            prev_byte = current_byte

def search_nasa_table(address):
    for key in NASA_REPO:
        if NASA_REPO[key]['address'].lower() == address.lower():
            return key
        
def is_valid_rawvalue(rawvalue: bytes) -> bool:
    return all(0x20 <= b <= 0x7E or b in (0x00, 0xFF) for b in rawvalue)  
          
async def process_packet(buffer, config):
    try:
        nasa_packet = NASAPacket()
        nasa_packet.parse(buffer)
        for msg in nasa_packet.packet_messages:
            if f"0x{msg.packet_message:04X}" in found_repo:
                msgvalue = None
                if msg.packet_message_type == 3:
                    msgvalue = ""

                    if is_valid_rawvalue(msg.packet_payload[1:-1]):
                        for byte in msg.packet_payload[1:-1]:
                            if byte != 0x00 and byte != 0xFF:
                                char = chr(byte) if 32 <= byte <= 126 else f"{byte}"
                                msgvalue += char
                            else:
                                msgvalue += " "
                        msgvalue = msgvalue.strip()
                    else:
                        msgvalue = "".join([f"{int(x)}" for x in msg.packet_payload])
                else:
                    msgvalue = int.from_bytes(msg.packet_payload, byteorder='big', signed=True)
                if msgvalue != found_repo[f"0x{msg.packet_message:04X}"]['packed_value']:
                    line = f" {hex(msg.packet_message):<6} | {msg.packet_message_type} | {found_repo[f"0x{msg.packet_message:04X}"]['packed_value']} -> {msgvalue} |"
                    print(line)
    except Exception as e:
        pass

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError as e:
        print(f"Runtime error: {e}")