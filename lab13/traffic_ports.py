from collections import defaultdict
import time
from scapy.all import sniff, IP, TCP, UDP

stats = defaultdict(int)

def handle(pkt):
    if IP in pkt:
        proto = pkt[IP].proto
        length = len(pkt)
        if TCP in pkt:
            sport, dport = pkt[TCP].sport, pkt[TCP].dport
        elif UDP in pkt:
            sport, dport = pkt[UDP].sport, pkt[UDP].dport
        else:
            sport = dport = 0
        key = (sport, dport)
        stats[key] += length

if __name__ == "__main__":
    print("Sniffing... Ctrl+C to stop")
    sniff(prn=handle, store=False)
    print("\nReport:")
    for (sport, dport), bytes_ in stats.items():
        print(f"{sport}->{dport}: {bytes_} bytes") 