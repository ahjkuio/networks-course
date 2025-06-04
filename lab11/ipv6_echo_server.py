import socket
import argparse


def serve(port):
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('::', port))
    s.listen(5)
    print(f'server listening on [::]:{port}')
    try:
        while True:
            conn, addr = s.accept()
            with conn:
                print('connection from', addr)
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    conn.sendall(data.upper())
    finally:
        s.close()


def main():
    p = argparse.ArgumentParser(description='IPv6 echo server (upper-case)')
    p.add_argument('-p', '--port', type=int, default=12345)
    args = p.parse_args()
    serve(args.port)


if __name__ == '__main__':
    main() 