import socket
import threading
import sys
import time
from urllib.parse import urlsplit

LOG_FILE = "proxy.log"
BUFFER_SIZE = 8192

def log(entry: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {entry}\n")


def recv_exact(sock: socket.socket, length: int) -> bytes:
    data = b""
    while len(data) < length:
        part = sock.recv(length - len(data))
        if not part:
            break
        data += part
    return data


def handle_client(client_sock: socket.socket):
    try:
        request = b""
        while b"\r\n\r\n" not in request:
            chunk = client_sock.recv(BUFFER_SIZE)
            if not chunk:
                return
            request += chunk
        header_data, remainder = request.split(b"\r\n\r\n", 1)
        header_lines = header_data.decode("utf-8", errors="ignore").split("\r\n")
        method, url, protocol = header_lines[0].split()
        headers = {}
        for line in header_lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        body = remainder
        if method.upper() == "POST" and "content-length" in headers:
            length = int(headers["content-length"])
            if len(body) < length:
                body += recv_exact(client_sock, length - len(body))

        if not url.startswith("http://") and "host" in headers:
            url = f"http://{headers['host']}{url}"

        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        try:
            server = socket.create_connection((host, port))
        except Exception as e:
            msg = f"HTTP/1.1 502 Bad Gateway\r\nContent-Length:0\r\n\r\n"
            client_sock.sendall(msg.encode())
            log(f"{method} {url} -> 502")
            return

        # rebuild request for origin server
        req_lines = [f"{method} {path} {protocol}"]
        for k, v in headers.items():
            if k in ("proxy-connection",):
                continue
            req_lines.append(f"{k.capitalize()}: {v}")
        req_lines.append("Connection: close")
        forward = "\r\n".join(req_lines).encode() + b"\r\n\r\n" + body

        server.sendall(forward)

        status_line_parsed = False
        code = "?"
        while True:
            data = server.recv(BUFFER_SIZE)
            if not data:
                break
            if not status_line_parsed:
                try:
                    line = data.split(b"\r\n", 1)[0].decode()
                    code = line.split()[1]
                except Exception:
                    pass
                status_line_parsed = True
            client_sock.sendall(data)
        log(f"{method} {url} -> {code}")
    except Exception as e:
        try:
            client_sock.sendall(b"HTTP/1.1 500 Internal Server Error\r\nContent-Length:0\r\n\r\n")
        except Exception:
            pass
    finally:
        client_sock.close()


def main():
    port = 8888
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("usage: proxy.py [port]")
            return
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    sock.listen(100)
    print(f"Proxy listening on port {port}")
    try:
        while True:
            client, _ = sock.accept()
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    main() 