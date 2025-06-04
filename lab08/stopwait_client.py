import os
import random
import socket
import struct
import sys
from pathlib import Path

from checksum import compute_checksum, valid_checksum

LOSS_PROB = 0.3
HEADER_FMT = "!BBH"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
FLAG_DATA = 0
FLAG_ACK = 1
FLAG_FIN = 2
DEFAULT_TIMEOUT = 1.0
PACKET_SIZE = 1024


def unreliable_send(sock: socket.socket, data: bytes, addr):
    if random.random() < LOSS_PROB:
        print("[drop] packet lost on send")
        return
    sock.sendto(data, addr)


def build_packet(seq: int, flag: int, payload: bytes) -> bytes:
    header = struct.pack(HEADER_FMT, seq, flag, len(payload))
    checksum = compute_checksum(header + payload)
    return header + payload + struct.pack("!H", checksum)


def main():
    if len(sys.argv) < 4:
        print(f"Usage: python {sys.argv[0]} <server_ip> <server_port> <file_path> [timeout] [pkt_size]")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    file_path = Path(sys.argv[3])
    timeout = float(sys.argv[4]) if len(sys.argv) >= 5 else DEFAULT_TIMEOUT
    pkt_size = int(sys.argv[5]) if len(sys.argv) >= 6 else PACKET_SIZE

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    seq = 0

    with file_path.open("rb") as f:
        while True:
            chunk = f.read(pkt_size)
            if not chunk:
                break
            packet = build_packet(seq, FLAG_DATA, chunk)
            while True:
                unreliable_send(sock, packet, (server_ip, server_port))
                try:
                    data, _ = sock.recvfrom(1024)
                    # возможно потеря ACK
                    if random.random() < LOSS_PROB:
                        print("[drop] incoming ACK lost")
                        raise socket.timeout
                    if len(data) < HEADER_SIZE + 2:
                        raise socket.timeout
                    r_seq, flag, _ = struct.unpack_from(HEADER_FMT, data)
                    r_checksum = struct.unpack("!H", data[-2:])[0]
                    if flag != FLAG_ACK or not valid_checksum(data[:-2], r_checksum):
                        raise socket.timeout
                    if r_seq == seq:
                        print(f"[ack] seq {seq}")
                        seq ^= 1
                        break
                except socket.timeout:
                    print(f"[ret] timeout, resend seq {seq}")
                    continue

    # отправляем FIN
    fin_pkt = build_packet(seq, FLAG_FIN, b"")
    while True:
        unreliable_send(sock, fin_pkt, (server_ip, server_port))
        try:
            data, _ = sock.recvfrom(1024)
            r_seq, flag, _ = struct.unpack_from(HEADER_FMT, data)
            r_checksum = struct.unpack("!H", data[-2:])[0]
            if flag == FLAG_ACK and r_seq == seq and valid_checksum(data[:-2], r_checksum):
                print("[done] transfer complete")
                break
        except socket.timeout:
            print("[ret] resend FIN")
            continue

    sock.close()
    print("client finished")


if __name__ == "__main__":
    main() 