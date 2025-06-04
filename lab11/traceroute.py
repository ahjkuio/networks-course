import socket
import struct
import time
import select
import argparse

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0
ICMP_TIME_EXCEEDED = 11
ICMP_DEST_UNREACH = 3


def checksum(data: bytes) -> int:
    s = 0
    for i in range(0, len(data), 2):
        w = data[i] + (data[i + 1] << 8) if i + 1 < len(data) else data[i]
        s = s + w
    s = (s >> 16) + (s & 0xFFFF)
    s = s + (s >> 16)
    return ~s & 0xFFFF


def build_packet(seq: int, pid: int) -> bytes:
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, pid, seq)
    payload = struct.pack("!d", time.time())
    cs = checksum(header + payload)
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, cs, pid, seq)
    return header + payload


def traceroute(dest_name: str, count: int, max_hops: int, timeout: float, proto: str):
    try:
        dest_addr = socket.gethostbyname(dest_name)
    except socket.gaierror as e:
        print(f"Cannot resolve {dest_name}: {e}")
        return

    print(f"traceroute to {dest_name} ({dest_addr}), {max_hops} hops max, {count} probes per hop")
    pid = int((id(timeout) * time.time()) % 65535)

    base_port = 33434  # для UDP
    for ttl in range(1, max_hops + 1):
        print(f"{ttl:2} ", end="", flush=True)
        hop_addr = None
        for seq in range(count):
            # сокет отправки зависит от протокола
            if proto == "icmp":
                send_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            else:
                send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            send_sock.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)

            # приём всегда через raw ICMP
            recv_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            recv_sock.settimeout(timeout)

            # отправка пакета
            if proto == "icmp":
                packet = build_packet(seq, pid)
                send_sock.sendto(packet, (dest_addr, 0))
            else:
                packet = b''
                send_sock.sendto(packet, (dest_addr, base_port + ttl))
            send_time = time.time()

            addr = None
            rtt = None
            try:
                while True:
                    rec_packet, addr = recv_sock.recvfrom(512)
                    icmp_header = rec_packet[20:28]
                    icmp_type, code, _, p_id, sequence = struct.unpack("!BBHHH", icmp_header)
                    reached = (
                        (proto == "icmp" and icmp_type == ICMP_ECHO_REPLY) or
                        (proto == "udp" and icmp_type == ICMP_DEST_UNREACH)
                    )
                    if icmp_type == ICMP_TIME_EXCEEDED or reached:
                        recv_time = time.time()
                        rtt = (recv_time - send_time) * 1000
                        hop_addr = addr[0]
                        break
            except socket.timeout:
                pass
            finally:
                recv_sock.close()
            if rtt is None:
                print(" *", end="", flush=True)
            else:
                print(f" {rtt:.1f} ms", end="", flush=True)
        if hop_addr:
            try:
                host = socket.gethostbyaddr(hop_addr)[0]
            except socket.herror:
                host = hop_addr
            print(f"  {host} [{hop_addr}]")
        else:
            print()
        if hop_addr == dest_addr:
            break


def main():
    parser = argparse.ArgumentParser(description="Simple traceroute using ICMP")
    parser.add_argument("destination", help="Destination host")
    parser.add_argument("-c", "--count", type=int, default=3, help="Packets per hop")
    parser.add_argument("-m", "--max-hops", type=int, default=30, help="Max hops to probe")
    parser.add_argument("-t", "--timeout", type=float, default=2.0, help="Timeout per probe (s)")
    parser.add_argument("--proto", choices=["icmp", "udp"], default="icmp", help="Probe protocol")
    args = parser.parse_args()
    if os.geteuid() != 0:
        print("Run as root to create raw sockets.")
        return
    traceroute(args.destination, args.count, args.max_hops, args.timeout, args.proto)


if __name__ == "__main__":
    import os
    main() 