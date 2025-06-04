import socket
import sys
import time

HOST = "0.0.0.0"
PORT = 13000
TIMEOUT = 3

if len(sys.argv) > 1:
    PORT = int(sys.argv[1])
if len(sys.argv) > 2:
    TIMEOUT = int(sys.argv[2])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
sock.settimeout(1)
print(f"heartbeat server at {HOST}:{PORT}, timeout={TIMEOUT}s")

clients = {}

def check_dead():
    now = time.time()
    for addr, info in list(clients.items()):
        last_t = info['time']
        if now - last_t > TIMEOUT:
            print(f"{addr} seems offline")
            del clients[addr]

while True:
    try:
        data, addr = sock.recvfrom(1024)
    except socket.timeout:
        check_dead()
        continue
    now = time.time()
    seq, sent_ts = map(float, data.decode().split())
    seq = int(seq)
    diff = now - sent_ts
    info = clients.get(addr, {"seq": -1, "time": now})
    lost = seq - info["seq"] - 1
    if lost > 0 and info["seq"] != -1:
        print(f"{lost} packet(s) lost from {addr}")
    print(f"{addr} seq={seq} diff={diff:.3f}s")
    clients[addr] = {"seq": seq, "time": now} 