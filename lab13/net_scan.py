import ipaddress
import sys
from scapy.all import ARP, Ether, srp


def scan(network):
    ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=str(network)), timeout=2, verbose=0)
    hosts = []
    for sent, rcv in ans:
        hosts.append((rcv.psrc, rcv.hwsrc))
    return hosts

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: net_scan.py 192.168.1.0/24")
        sys.exit(1)
    net = ipaddress.ip_network(sys.argv[1], strict=False)
    hosts = scan(net)
    for ip, mac in hosts:
        print(f"{ip}\t{mac}") 