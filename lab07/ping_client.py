import socket
import sys
import time

if len(sys.argv) < 2:
    print("usage: python3 ping_client.py <server_host> [port]")
    sys.exit(1)

server = sys.argv[1]
port = int(sys.argv[2]) if len(sys.argv) > 2 else 12000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(1)

for seq in range(1, 11):
    msg = f"Ping {seq} {time.time()}".encode()
    start = time.time()
    sock.sendto(msg, (server, port))
    try:
        data, _ = sock.recvfrom(1024)
        rtt = (time.time() - start)
        print(f"Reply from {server}: seq={seq} rtt={rtt:.3f}s msg={data.decode()}")
    except socket.timeout:
        print("Request timed out") 