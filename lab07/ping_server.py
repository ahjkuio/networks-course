import random
import socket
import sys

HOST = "0.0.0.0"
PORT = 12000
LOSS_PROB = 0.2

if len(sys.argv) > 1:
    PORT = int(sys.argv[1])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
print(f"ping server listening at {HOST}:{PORT}")

while True:
    data, addr = sock.recvfrom(1024)
    if random.random() < LOSS_PROB:
        # simulate loss
        continue
    sock.sendto(data.upper(), addr) 