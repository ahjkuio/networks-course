import binascii
import random
import textwrap

POLY = 0x1021  # CRC-16-CCITT


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ POLY if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def encode_packet(payload: bytes) -> bytes:
    c = crc16(payload)
    return payload + c.to_bytes(2, "big")


def corrupt(b: bytes, bits: int = 1) -> bytes:
    b = bytearray(b)
    for _ in range(bits):
        i = random.randrange(len(b))
        bit = 1 << random.randrange(8)
        b[i] ^= bit
    return bytes(b)


if __name__ == "__main__":
    text = input("Введите текст: ").encode()
    # chunks = textwrap.wrap(text.decode(errors="ignore"), 5)
    chunk_size = 5
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    for idx, chunk in enumerate(chunks):
        pld = chunk # chunk is already bytes
        pkt = encode_packet(pld)
        if random.random() < 0.3:
            pkt = corrupt(pkt)
        recv_payload, recv_crc = pkt[:-2], pkt[-2:]
        ok = crc16(recv_payload) == int.from_bytes(recv_crc, "big")
        print(f"#{idx:02} data={recv_payload!r} pkt={pkt.hex()} crc={recv_crc.hex()} -> {'OK' if ok else 'ERR'}") 