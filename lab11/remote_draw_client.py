import socket
import tkinter as tk
import threading

PORT = 50007


def main():
    host = input('server ip: ')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, PORT))

    root = tk.Tk()
    root.title('Client canvas')
    canvas = tk.Canvas(root, width=800, height=600, bg='white')
    canvas.pack()

    prev = {'x': None, 'y': None}

    def on_move(event):
        x, y = event.x, event.y
        if prev['x'] is not None:
            canvas.create_line(prev['x'], prev['y'], x, y)
            msg = f"{x} {y} ".encode()
            try:
                s.sendall(msg)
            except OSError:
                pass
        prev['x'], prev['y'] = x, y

    def on_release(event):
        prev['x'], prev['y'] = None, None
        try:
            s.sendall(b"END\n")
        except OSError:
            pass

    canvas.bind('<B1-Motion>', on_move)
    canvas.bind('<ButtonRelease-1>', on_release)

    root.mainloop()
    s.close()


if __name__ == '__main__':
    main() 