import argparse
import os
import struct
import select
import socket
import time
from collections import deque

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0


def checksum(source: bytes) -> int:
    if len(source) % 2:
        source += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(source) // 2), source))
    s = (s >> 16) + (s & 0xFFFF)
    s += s >> 16
    return ~s & 0xFFFF


class Pinger:
    def __init__(self, host: str, count: int = 4, timeout: float = 1.0):
        self.dest_ip = socket.gethostbyname(host)
        self.count = count
        self.timeout = timeout
        self.pid = os.getpid() & 0xFFFF
        self.rtts = deque()

    def _build_packet(self, seq):
        header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, self.pid, seq)
        data = struct.pack("!d", time.time())
        chk = checksum(header + data)
        header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, chk, self.pid, seq)
        return header + data

    def _send(self, sock, seq):
        sock.sendto(self._build_packet(seq), (self.dest_ip, 1))

    def _receive(self, sock, seq):
        start = time.time()
        while True:
            remain = self.timeout - (time.time() - start)
            if remain <= 0:
                return None
            ready = select.select([sock], [], [], remain)
            if not ready[0]:
                return None
            recv_time = time.time()
            packet, _ = sock.recvfrom(1024)
            icmp_type, _, _, p_id, p_seq = struct.unpack("!BBHHH", packet[20:28])
            if p_id != self.pid or icmp_type != ICMP_ECHO_REPLY or p_seq != seq:
                continue
            send_time, = struct.unpack("!d", packet[28:36])
            return (recv_time - send_time) * 1000

    def run(self):
        print(f"PING {self.dest_ip} with {self.count} packets")
        with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp")) as sock:
            for seq in range(1, self.count + 1):
                self._send(sock, seq)
                rtt = self._receive(sock, seq)
                if rtt is None:
                    print(f"seq={seq} timeout")
                else:
                    self.rtts.append(rtt)
                    print(f"seq={seq} time={rtt:.2f} ms")
                time.sleep(1)
        self._summary()

    def _summary(self):
        tx = self.count
        rx = len(self.rtts)
        loss = (1 - rx / tx) * 100
        print("--- statistics ---")
        print(f"{tx} packets transmitted, {rx} received, {loss:.0f}% packet loss")
        if rx:
            print(f"rtt min/avg/max = {min(self.rtts):.2f}/{sum(self.rtts)/rx:.2f}/{max(self.rtts):.2f} ms")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("-c", type=int, default=4)
    args = parser.parse_args()
    try:
        Pinger(args.host, args.c).run()
    except PermissionError:
        print("Need root privileges.")


if __name__ == "__main__":
    main() 