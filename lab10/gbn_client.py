import argparse
import os
import socket
import struct
import time

SEG_SIZE = 1024
HDR_FMT = "!I?"  # seq, fin flag
ACK_FMT = "!I"
WINDOW = 4
TIMEOUT = 0.5


def log(msg):
    print(f"[CLIENT {time.strftime('%H:%M:%S')}] {msg}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ip")
    parser.add_argument("port", type=int)
    parser.add_argument("file")
    args = parser.parse_args()

    with open(args.file, "rb") as f:
        data = f.read()

    segments = [data[i:i + SEG_SIZE] for i in range(0, len(data), SEG_SIZE)]
    total = len(segments)

    send_base = 0
    next_seq = 0
    timers = {}

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(0.1)
        addr = (args.ip, args.port)
        while send_base < total:
            while next_seq < total and next_seq - send_base < WINDOW:
                fin = next_seq == total - 1
                pkt = struct.pack(HDR_FMT, next_seq, fin) + segments[next_seq]
                s.sendto(pkt, addr)
                timers[next_seq] = time.time()
                log(f"send seq={next_seq}")
                next_seq += 1
            try:
                pkt, _ = s.recvfrom(8)
                ack, = struct.unpack(ACK_FMT, pkt)
                log(f"ack {ack}")
                if ack >= send_base:
                    send_base = ack + 1
                    for k in list(timers.keys()):
                        if k <= ack:
                            timers.pop(k, None)
            except socket.timeout:
                pass
            # handle timeout
            now = time.time()
            for seq in list(timers.keys()):
                if now - timers[seq] > TIMEOUT:
                    fin = seq == total - 1
                    pkt = struct.pack(HDR_FMT, seq, fin) + segments[seq]
                    s.sendto(pkt, addr)
                    timers[seq] = now
                    log(f"resend seq={seq}")
        log("done")


if __name__ == "__main__":
    main() 