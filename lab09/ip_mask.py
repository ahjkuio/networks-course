#!/usr/bin/env python3
"""Console utility to print the first non-loopback IPv4 address and its subnet mask.
Works on Linux, requires the system `ip` command (iproute2)."""

import subprocess
import re
import sys

PATTERN = re.compile(r"inet (?P<ip>\d+\.\d+\.\d+\.\d+)/(\d+)")


def get_ip_and_mask() -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["ip", "-o", "-f", "inet", "addr", "show"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        sys.exit("failed to execute `ip` – is iproute2 installed?")

    for line in result.stdout.splitlines():
        if " lo " in line:  # skip loopback
            continue
        m = PATTERN.search(line)
        if m:
            ip = m.group("ip")
            cidr = int(line.split("/")[1].split()[0])
            # convert CIDR to dotted mask
            mask_int = (0xFFFFFFFF >> (32 - cidr)) << (32 - cidr)
            mask = ".".join(str((mask_int >> (8 * i)) & 0xFF) for i in reversed(range(4)))
            return ip, mask
    sys.exit("no active IPv4 interfaces found")


def main() -> None:
    ip, mask = get_ip_and_mask()
    print(f"IP address: {ip}")
    print(f"Subnet mask: {mask}")


if __name__ == "__main__":
    main() 