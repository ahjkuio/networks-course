import argparse
import os
import struct
import select
import socket
import time
from collections import deque

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0
ICMP_DEST_UNREACH = 3

ERROR_CODES = {
    0: "Сеть назначения недоступна",
    1: "Хост назначения недоступен",
}


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
                return None, None
            ready = select.select([sock], [], [], remain)
            if not ready[0]:
                return None, None
            recv_time = time.time()
            packet, _ = sock.recvfrom(1024)
            icmp_type, code = packet[20], packet[21]
            if icmp_type == ICMP_DEST_UNREACH:
                return None, code
            icmp_type, _, _, p_id, p_seq = struct.unpack("!BBHHH", packet[20:28])
            if p_id != self.pid or icmp_type != ICMP_ECHO_REPLY or p_seq != seq:
                continue
            send_time, = struct.unpack("!d", packet[28:36])
            return (recv_time - send_time) * 1000, None

    def run(self):
        print(f"PING {self.dest_ip} with {self.count} packets")
        with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp")) as sock:
            for seq in range(1, self.count + 1):
                self._send(sock, seq)
                rtt, err = self._receive(sock, seq)
                if rtt is not None:
                    self.rtts.append(rtt)
                    print(f"seq={seq} time={rtt:.2f} ms")
                elif err is not None:
                    msg = ERROR_CODES.get(err, f"ICMP code {err}")
                    print(f"seq={seq} ошибка: {msg}")
                else:
                    print(f"seq={seq} timeout")
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
    parser.add_argument("-W", "--timeout", type=float, default=1.0)
    args = parser.parse_args()
    try:
        Pinger(args.host, args.c, args.timeout).run()
    except PermissionError:
        print("Need root privileges.")


if __name__ == "__main__":
    main() 