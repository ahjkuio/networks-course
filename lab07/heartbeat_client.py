import socket
import sys
import time

if len(sys.argv) < 2:
    print("usage: python3 heartbeat_client.py <server_host> [port] [interval]")
    sys.exit(1)

server = sys.argv[1]
port = int(sys.argv[2]) if len(sys.argv) > 2 else 13000
interval = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

seq = 0
print(f"sending heartbeats to {server}:{port} every {interval}s")
try:
    while True:
        seq += 1
        msg = f"{seq} {time.time()}".encode()
        sock.sendto(msg, (server, port))
        time.sleep(interval)
except KeyboardInterrupt:
    print("stopped") 