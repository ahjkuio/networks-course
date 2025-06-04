import random
import socket
import struct
import sys
from pathlib import Path

from checksum import compute_checksum, valid_checksum

LOSS_PROB = 0.3  # 30% потерь
HEADER_FMT = "!BBH"  # seq, flag, length
HEADER_SIZE = struct.calcsize(HEADER_FMT)

FLAG_DATA = 0
FLAG_ACK = 1
FLAG_FIN = 2


def unreliable_send(sock: socket.socket, data: bytes, addr):
    if random.random() < LOSS_PROB:
        # эмулируем потерю
        print("[drop] ACK lost")
        return
    sock.sendto(data, addr)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <port> <output_file>")
        sys.exit(1)

    port = int(sys.argv[1])
    out_path = Path(sys.argv[2])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    print(f"Server listening on *:{port}, writing to {out_path}")

    expected_seq = 0
    with out_path.open("wb") as out_file:
        while True:
            data, addr = sock.recvfrom(4096)
            # имитация потери входящего пакета
            if random.random() < LOSS_PROB:
                print("[drop] packet from", addr)
                continue

            if len(data) < HEADER_SIZE + 2:
                continue  # мусор

            seq, flag, length = struct.unpack_from(HEADER_FMT, data)
            payload = data[HEADER_SIZE:-2]
            recv_checksum = struct.unpack("!H", data[-2:])[0]
            if not valid_checksum(data[:-2], recv_checksum):
                print("[err] bad checksum, seq", seq)
                continue

            if flag == FLAG_FIN:
                print("[fin] finishing transfer")
                ack_pkt = build_packet(seq, FLAG_ACK, b"")
                unreliable_send(sock, ack_pkt, addr)
                break

            if flag == FLAG_DATA and seq == expected_seq:
                out_file.write(payload[:length])
                expected_seq ^= 1
                print(f"[ok] got seq {seq}, wrote {length} bytes")
            else:
                print(f"[dup] got seq {seq}, expected {expected_seq}")

            # всегда отправляем ACK с текущим seq
            ack_pkt = build_packet(seq, FLAG_ACK, b"")
            unreliable_send(sock, ack_pkt, addr)



def build_packet(seq: int, flag: int, payload: bytes) -> bytes:
    header = struct.pack(HEADER_FMT, seq, flag, len(payload))
    checksum = compute_checksum(header + payload)
    return header + payload + struct.pack("!H", checksum)


if __name__ == "__main__":
    main() 