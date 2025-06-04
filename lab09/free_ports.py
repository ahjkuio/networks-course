#!/usr/bin/env python3
"""Scan given TCP port range on provided IP and list ports that are free (can bind)."""

import argparse
import socket
from contextlib import closing


def is_free(ip: str, port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((ip, port))
        except OSError:
            return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="List free TCP ports in range for given IP")
    parser.add_argument("ip", help="IP address to test")
    parser.add_argument("start", type=int, help="start port (inclusive)")
    parser.add_argument("end", type=int, help="end port (inclusive)")
    args = parser.parse_args()

    free = [p for p in range(args.start, args.end + 1) if is_free(args.ip, p)]
    for p in free:
        print(p)


if __name__ == "__main__":
    main() 