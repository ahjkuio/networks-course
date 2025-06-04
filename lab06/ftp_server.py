import socket
import threading
import os
from pathlib import Path

HOST = '0.0.0.0'
PORT = 2121  # нестандартный, чтобы не требовать прав суперпользователя

RESPONSES = {
    'WELCOME': '220 Simple FTP Server ready\r\n',
    'USER_OK': '331 Username OK, need password\r\n',
    'LOGIN_OK': '230 Login successful\r\n',
    'PWD': '257 "{cwd}" is current directory\r\n',
    'CWD_OK': '250 Directory changed\r\n',
    'PORT_OK': '200 Active data connection established\r\n',
    'QUIT': '221 Goodbye\r\n',
    'TYPE_OK': '200 Type set to I\r\n',
    'TRANS_START': '150 Opening data connection\r\n',
    'TRANS_DONE': '226 Transfer complete\r\n',
    'FILE_NOT_FOUND': '550 File not found\r\n',
    'DELETE_OK': '250 Delete OK\r\n',
    'SYNTAX_ERR': '500 Syntax error\r\n',
}


def make_data_address(args: str):
    parts = args.split(',')
    if len(parts) != 6:
        return None
    ip = '.'.join(parts[:4])
    port = (int(parts[4]) << 8) + int(parts[5])
    return ip, port


def handle_client(conn: socket.socket, addr):
    cwd = Path.cwd()
    data_addr = None
    conn.sendall(RESPONSES['WELCOME'].encode())

    while True:
        cmd_line = conn.recv(1024).decode('utf-8').strip()
        if not cmd_line:
            break
        parts = cmd_line.split(' ', 1)
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ''

        if cmd == 'USER':
            conn.sendall(RESPONSES['USER_OK'].encode())
        elif cmd == 'PASS':
            conn.sendall(RESPONSES['LOGIN_OK'].encode())
        elif cmd == 'PWD':
            conn.sendall(RESPONSES['PWD'].format(cwd=cwd).encode())
        elif cmd == 'CWD':
            target = (cwd / arg).resolve()
            if target.is_dir():
                cwd = target
                conn.sendall(RESPONSES['CWD_OK'].encode())
            else:
                conn.sendall(RESPONSES['FILE_NOT_FOUND'].encode())
        elif cmd == 'TYPE':
            conn.sendall(RESPONSES['TYPE_OK'].encode())
        elif cmd == 'PORT':
            data_addr = make_data_address(arg)
            if data_addr:
                conn.sendall(RESPONSES['PORT_OK'].encode())
            else:
                conn.sendall(RESPONSES['SYNTAX_ERR'].encode())
        elif cmd == 'NLST':
            if not data_addr:
                conn.sendall(RESPONSES['SYNTAX_ERR'].encode())
                continue
            conn.sendall(RESPONSES['TRANS_START'].encode())
            with socket.socket() as data_sock:
                data_sock.connect(data_addr)
                listing = '\r\n'.join(os.listdir(cwd)) + '\r\n'
                data_sock.sendall(listing.encode())
            conn.sendall(RESPONSES['TRANS_DONE'].encode())
        elif cmd == 'RETR':
            path = cwd / arg
            if not path.exists():
                conn.sendall(RESPONSES['FILE_NOT_FOUND'].encode())
                continue
            if not data_addr:
                conn.sendall(RESPONSES['SYNTAX_ERR'].encode())
                continue
            conn.sendall(RESPONSES['TRANS_START'].encode())
            with socket.socket() as data_sock, path.open('rb') as f:
                data_sock.connect(data_addr)
                while chunk := f.read(1024):
                    data_sock.sendall(chunk)
            conn.sendall(RESPONSES['TRANS_DONE'].encode())
        elif cmd == 'STOR':
            if not data_addr:
                conn.sendall(RESPONSES['SYNTAX_ERR'].encode())
                continue
            conn.sendall(RESPONSES['TRANS_START'].encode())
            with socket.socket() as data_sock, (cwd / arg).open('wb') as f:
                data_sock.connect(data_addr)
                while True:
                    data = data_sock.recv(1024)
                    if not data:
                        break
                    f.write(data)
            conn.sendall(RESPONSES['TRANS_DONE'].encode())
        elif cmd == 'DELE':
            path = cwd / arg
            if path.is_file():
                try:
                    path.unlink()
                    conn.sendall(RESPONSES['DELETE_OK'].encode())
                except Exception:
                    conn.sendall(RESPONSES['FILE_NOT_FOUND'].encode())
            else:
                conn.sendall(RESPONSES['FILE_NOT_FOUND'].encode())
        elif cmd == 'QUIT':
            conn.sendall(RESPONSES['QUIT'].encode())
            break
        else:
            conn.sendall(RESPONSES['SYNTAX_ERR'].encode())

    conn.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Server listening on {HOST}:{PORT}')
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()


if __name__ == '__main__':
    main() 