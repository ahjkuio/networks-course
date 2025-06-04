import socket
import threading
import tkinter as tk

PORT = 50007


def handle_conn(conn, canvas):
    prev = None
    with conn:
        while True:
            data = conn.recv(64)
            if not data:
                break
            try:
                parts = data.decode().strip().split()
                if parts and parts[0] == "END":
                    prev = None
                    continue
                for i in range(0, len(parts), 2):
                    x = int(parts[i])
                    y = int(parts[i+1])
                    if prev is not None:
                        canvas.create_line(prev[0], prev[1], x, y)
                    prev = (x, y)
            except Exception:
                continue


def main():
    root = tk.Tk()
    root.title('Server canvas')
    canvas = tk.Canvas(root, width=800, height=600, bg='white')
    canvas.pack()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('0.0.0.0', PORT))
    s.listen(1)
    print('waiting for connection on', PORT)
    conn, addr = s.accept()
    print('connected from', addr)

    threading.Thread(target=handle_conn, args=(conn, canvas), daemon=True).start()
    root.mainloop()


if __name__ == '__main__':
    main() 