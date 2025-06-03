import socket
import threading
import sys
import os
import time
import hashlib
import json
from urllib.parse import urlsplit

CACHE_DIR = "lab04_cache"
LOG_FILE = "proxy_blacklist.log"
# Файл со списком блокировок – рядом со скриптом
BLACKLIST_FILE = os.path.join(os.path.dirname(__file__), "blacklist.txt")
BUFFER = 8192

os.makedirs(CACHE_DIR, exist_ok=True)

# load blacklist once
if os.path.exists(BLACKLIST_FILE):
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as bl:
        BL_ENTRIES = [l.strip() for l in bl if l.strip() and not l.startswith("#")]
else:
    BL_ENTRIES = []

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()

def meta_path(h: str) -> str:
    return os.path.join(CACHE_DIR, f"{h}.meta")

def body_path(h: str) -> str:
    return os.path.join(CACHE_DIR, f"{h}.body")

def blocked(url: str) -> bool:
    for entry in BL_ENTRIES:
        if entry in url:
            return True
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    for entry in BL_ENTRIES:
        if entry == host or host.endswith("." + entry):
            return True
    return False

def read_headers(sock: socket.socket):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(BUFFER)
        if not chunk:
            break
        data += chunk
    header_bytes, rest = data.split(b"\r\n\r\n", 1)
    return header_bytes, rest

def parse_headers(header_bytes: bytes):
    lines = header_bytes.decode(errors="ignore").split("\r\n")
    status_line = lines[0]
    code = status_line.split()[1]
    headers = {}
    for l in lines[1:]:
        if ":" in l:
            k, v = l.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return status_line, code, headers

def rebuild_request(method: str, path: str, proto: str, hdrs: dict[str,str], body: bytes):
    lines = [f"{method} {path} {proto}"]
    for k, v in hdrs.items():
        if k == "proxy-connection":
            continue
        lines.append(f"{k.capitalize()}: {v}")
    lines.append("Connection: close")
    return "\r\n".join(lines).encode() + b"\r\n\r\n" + body

def send_block(client: socket.socket, url: str):
    html = f"<html><body><h1>Blocked</h1><p>Access to {url} is denied.</p></body></html>".encode()
    resp = (
        "HTTP/1.1 403 Forbidden\r\n" +
        f"Content-Length: {len(html)}\r\n" +
        "Content-Type: text/html\r\n" +
        "Connection: close\r\n\r\n"
    ).encode() + html
    client.sendall(resp)
    log(f"BLOCKED {url}")


def handle(client: socket.socket):
    try:
        req = b""
        while b"\r\n\r\n" not in req:
            chunk = client.recv(BUFFER)
            if not chunk:
                return
            req += chunk
        header_b, body = req.split(b"\r\n\r\n", 1)
        first, *rest = header_b.decode(errors="ignore").split("\r\n")
        method, url, proto = first.split()
        hdrs = {}
        for l in rest:
            if ":" in l:
                k, v = l.split(":", 1)
                hdrs[k.strip().lower()] = v.strip()
        if method.upper() == "POST" and "content-length" in hdrs:
            length = int(hdrs["content-length"])
            while len(body) < length:
                body += client.recv(length - len(body))
        if not url.startswith("http://") and "host" in hdrs:
            url = f"http://{hdrs['host']}{url}"

        # Blacklist check
        if blocked(url):
            send_block(client, url)
            return

        p = urlsplit(url)
        host, port = p.hostname, p.port or 80
        path = p.path or "/"
        if p.query:
            path += f"?{p.query}"
        hsh = url_hash(url)
        meta_f, body_f = meta_path(hsh), body_path(hsh)
        # conditional headers if cached
        if os.path.exists(meta_f):
            try:
                with open(meta_f, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("etag"):
                    hdrs["if-none-match"] = meta["etag"]
                if meta.get("last-modified"):
                    hdrs["if-modified-since"] = meta["last-modified"]
            except Exception:
                pass
        try:
            origin = socket.create_connection((host, port))
        except Exception:
            client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length:0\r\n\r\n")
            log(f"{method} {url} -> 502")
            return
        origin_req = rebuild_request(method, path, proto, hdrs, body)
        origin.sendall(origin_req)
        hdr_bytes, remainder = read_headers(origin)
        status_line, code, resp_headers = parse_headers(hdr_bytes)
        if code == "304" and os.path.exists(body_f):
            with open(body_f, "rb") as f:
                body_cached = f.read()
            client.sendall(b"HTTP/1.1 200 OK\r\n")
            resp_headers.pop("transfer-encoding", None)
            resp_headers["content-length"] = str(len(body_cached))
            for k, v in resp_headers.items():
                client.sendall(f"{k.capitalize()}: {v}\r\n".encode())
            client.sendall(b"\r\n" + body_cached)
            log(f"{method} {url} -> 200 (cache hit)")
            origin.close()
            return
        # forward and possibly store
        client.sendall(hdr_bytes + b"\r\n\r\n" + remainder)
        if code == "200":
            with open(body_f + ".tmp", "wb") as out:
                out.write(remainder)
                while True:
                    chunk = origin.recv(BUFFER)
                    if not chunk:
                        break
                    client.sendall(chunk)
                    out.write(chunk)
            os.replace(body_f + ".tmp", body_f)
            meta = {
                "etag": resp_headers.get("etag"),
                "last-modified": resp_headers.get("last-modified"),
                "saved": time.time(),
            }
            with open(meta_f, "w", encoding="utf-8") as mf:
                json.dump(meta, mf)
        else:
            while True:
                chunk = origin.recv(BUFFER)
                if not chunk:
                    break
                client.sendall(chunk)
        log(f"{method} {url} -> {code}")
    except Exception:
        try:
            client.sendall(b"HTTP/1.1 500 Internal Server Error\r\nContent-Length:0\r\n\r\n")
        except Exception:
            pass
    finally:
        client.close()


def main():
    port = 8890
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", port))
    s.listen(100)
    print(f"Proxy(blacklist) on {port}")
    try:
        while True:
            c,_ = s.accept()
            threading.Thread(target=handle, args=(c,), daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        s.close()

if __name__ == "__main__":
    main() 