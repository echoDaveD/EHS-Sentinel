
import asyncio
import serial
import serial_asyncio
import MessageProcessor

class SerialReader(asyncio.Protocol):
    def __init__(self, buffer):
        self.buffer = buffer

    def data_received(self, data):
        for byte in data:
            self.buffer.append(byte)

async def process_buffer(buffer):
    while True:
        if buffer:
            if buffer[0] == 0x32:
                #print("Received 0x32 start of message")
                packet_size = ((buffer[1] << 8) | buffer[2]) +2
                print(f"Packet size: {packet_size}")
                # read till x34 or pockaetsize (in idela world, its the same)
                message = []
                message.append(buffer[0])
                for i in range(1, 256):
                    message.append(buffer[i])
                    if buffer[i] == 0x34  or i == packet_size-1:
                        hex_message = list(map(hex, message))
                        print(message)
                        print(f"Complete size: {i}/{packet_size} message: {message}")
                        print(f"Complete size: {i}/{packet_size} message: {hex_message}")
                        await MessageProcessor().process_message(message, packet_size)
                        del buffer[0:i]
                        break
            else:
                #print(f"Received unknown byte {buffer[0]} / {hex(buffer[0])}")
                buffer.pop(0)

        await asyncio.sleep(0.1)  # Simulierte Verarbeitungsverzoegerung

async def main():
    buffer = []
    loop = asyncio.get_running_loop()

    # Serielle Verbindung       ffnen (port und baudrate anpassen)
    transport, protocol = await serial_asyncio.create_serial_connection(
        loop, lambda: SerialReader(buffer), '/dev/ttyUSB0', baudrate=9600, parity=serial.PARITY_EVEN,
                     stopbits=serial.STOPBITS_ONE,
                     bytesize=serial.EIGHTBITS,
                     rtscts=True,
                     timeout=0

    )

    # Starte den asynchronen Buffer-Prozessor
    asyncio.create_task(process_buffer(buffer))

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        transport.close()

if __name__ == "__main__":
    asyncio.run(main())


