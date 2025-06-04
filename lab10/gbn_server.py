import argparse
import os
import socket
import struct
import time

SEG_SIZE = 1024
HDR_FMT = "!I?"  # seq (uint32) , fin flag (bool)
ACK_FMT = "!I"   # ack for seq


def log(msg):
    print(f"[SERVER {time.strftime('%H:%M:%S')}] {msg}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int)
    parser.add_argument("out", help="output file path")
    args = parser.parse_args()

    buf = {}
    expected = 0

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("0.0.0.0", args.port))
        log(f"listen {args.port}")
        with open(args.out, "wb") as f:
            while True:
                data, addr = s.recvfrom(SEG_SIZE + 8)
                if not data:
                    continue
                seq, fin = struct.unpack(HDR_FMT, data[:5])
                payload = data[5:]

                if seq == expected:
                    f.write(payload)
                    expected += 1
                    if fin:
                        log("file received")
                        s.sendto(struct.pack(ACK_FMT, seq), addr)
                        break
                # send ack of last correct
                ack_num = expected - 1 if expected else 0
                s.sendto(struct.pack(ACK_FMT, ack_num), addr)
                log(f"recv seq={seq} exp={expected} ack={ack_num}")
    log("done")


if __name__ == "__main__":
    main() 