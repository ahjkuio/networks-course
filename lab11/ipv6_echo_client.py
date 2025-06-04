import socket
import argparse


def run(host, port, message):
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(message.encode())
        data = s.recv(1024)
        print('received:', data.decode())


def main():
    p = argparse.ArgumentParser(description='IPv6 echo client')
    p.add_argument('host', help='IPv6 address of server')
    p.add_argument('-p', '--port', type=int, default=12345)
    p.add_argument('message', nargs='?', default='hello')
    args = p.parse_args()
    run(args.host, args.port, args.message)


if __name__ == '__main__':
    main() 