import socket
import sys
import time

if len(sys.argv) < 2:
    print("usage: python3 ping_client_stats.py <server_host> [port]")
    sys.exit(1)

server = sys.argv[1]
port = int(sys.argv[2]) if len(sys.argv) > 2 else 12000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(1)

sent = 0
recv = 0
rtts = []

for seq in range(1, 11):
    sent += 1
    msg = f"Ping {seq} {time.time()}".encode()
    start = time.time()
    sock.sendto(msg, (server, port))
    try:
        data, _ = sock.recvfrom(1024)
        rtt = time.time() - start
        rtts.append(rtt)
        recv += 1
        print(f"{len(data)} bytes from {server}: seq={seq} time={rtt*1000:.2f} ms")
    except socket.timeout:
        print("Request timed out")

print("\n--- ping statistics ---")
loss = (sent - recv) / sent * 100
print(f"{sent} packets transmitted, {recv} received, {loss:.0f}% packet loss")
if rtts:
    print(f"rtt min/avg/max = {min(rtts)*1000:.2f}/{(sum(rtts)/len(rtts))*1000:.2f}/{max(rtts)*1000:.2f} ms") 