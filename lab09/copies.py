#!/usr/bin/env python3
import tkinter as tk
from tkinter import Listbox, Frame, Label, Button, Entry, StringVar, LEFT, RIGHT, X, BOTH, END
import socket
import threading
import time
import random

BCAST_IP = "255.255.255.255"
DISCOVERY_PORT = 54545
APP_INTERVAL = 2.0
APP_TIMEOUT = APP_INTERVAL * 3

class CopiesApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Анализатор копий")

        self.active_instances = {}  # Stores {(ip, id_port): timestamp} for OTHERS
        self.my_identifier_port = random.randint(30000, 40000)
        self.my_ip = self._get_local_ip()
        self.my_key_tuple = (self.my_ip, self.my_identifier_port)

        # Top Frame for counts and interval
        top_frame = Frame(self.root)
        top_frame.pack(fill=X, padx=10, pady=5)

        count_outer_frame = Frame(top_frame)
        count_outer_frame.pack(side=LEFT)
        Label(count_outer_frame, text="Копий запущено:").pack(side=LEFT)
        self.count_display_var = StringVar(value="1")
        Label(count_outer_frame, textvariable=self.count_display_var).pack(side=LEFT)

        interval_outer_frame = Frame(top_frame)
        interval_outer_frame.pack(side=RIGHT, padx=(10,0)) # Add some padding to separate
        Label(interval_outer_frame, text="Ожидание, мс:").pack(side=LEFT)
        interval_entry = Entry(interval_outer_frame, width=7, justify='right')
        interval_entry.insert(0, str(int(APP_INTERVAL * 1000)))
        interval_entry.config(state='readonly')
        interval_entry.pack(side=LEFT)
        
        self.listbox = Listbox(self.root, width=45, height=10) # Adjusted height a bit
        self.listbox.pack(pady=(0,5), padx=10, fill=BOTH, expand=True)

        close_button = Button(self.root, text="Закрыть", command=self._on_closing_event)
        close_button.pack(pady=5)
        
        if not self._setup_network_socket():
            self.listbox.insert(END, "Ошибка: Сбой настройки сети.")
            self.count_display_var.set("Error")
            self.root.after(3000, self.root.destroy)
            return

        self.listener_thread = threading.Thread(target=self._network_listener, daemon=True)
        self.listener_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing_event)
        self._schedule_periodic_tasks()
        print(f"Мой экземпляр: {self.my_ip}:{self.my_identifier_port}")

    def _get_local_ip(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(0.1) # Prevent long block if no internet
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except OSError:
            # Fallback: try getting from hostname if specific connect fails
            try:
                return socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                return "127.0.0.1" # Absolute fallback

    def _setup_network_socket(self):
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.broadcast_socket.bind(("", DISCOVERY_PORT))
            return True
        except OSError as e:
            print(f"Критическая ошибка: Не удалось привязаться к порту {DISCOVERY_PORT}: {e}")
            return False

    def _network_listener(self):
        while True:
            try:
                data, addr = self.broadcast_socket.recvfrom(1024)
                message_str = data.decode(errors="ignore").strip()
                sender_ip = addr[0]

                parts = message_str.split()
                if not parts or len(parts) < 2:
                    continue
                command = parts[0]
                try:
                    sender_id_port = int(parts[1])
                except ValueError:
                    continue

                instance_key = (sender_ip, sender_id_port)

                if instance_key == self.my_key_tuple: # Message from self
                    continue
                
                current_time = time.time()
                if command == "HELLO":
                    if instance_key not in self.active_instances or \
                       self.active_instances.get(instance_key, 0) < current_time:
                        self.active_instances[instance_key] = current_time
                        # Respond to HELLO (from others) with an ALIVE message (also broadcast)
                        # This helps new joiners discover existing ones faster than just periodic HELLO
                        reply_message = f"ALIVE {self.my_identifier_port}".encode()
                        self.broadcast_socket.sendto(reply_message, (BCAST_IP, DISCOVERY_PORT))
                        self.root.after(0, self._update_gui_listbox)
                elif command == "ALIVE":
                    if instance_key not in self.active_instances or \
                       self.active_instances.get(instance_key, 0) < current_time: # Update if new or this ALIVE is newer
                        self.active_instances[instance_key] = current_time
                        self.root.after(0, self._update_gui_listbox)
                elif command == "BYE":
                    if instance_key in self.active_instances:
                        del self.active_instances[instance_key]
                        self.root.after(0, self._update_gui_listbox)

            except OSError: 
                break # Socket likely closed
            except Exception as e:
                print(f"Ошибка в слушателе: {e}")

    def _schedule_periodic_tasks(self):
        hello_message = f"HELLO {self.my_identifier_port}".encode()
        try:
            self.broadcast_socket.sendto(hello_message, (BCAST_IP, DISCOVERY_PORT))
        except OSError as e:
            print(f"Ошибка отправки HELLO: {e}")

        current_time = time.time()
        stale_keys = [
            key for key, ts in self.active_instances.items() 
            if current_time - ts > APP_TIMEOUT
        ]
        updated = False
        for key in stale_keys:
            if key in self.active_instances:
                del self.active_instances[key]
                updated = True
        
        if updated:
            self._update_gui_listbox() # Update GUI if any stale entries removed
        else: # If no stale entries removed, still ensure count and list might need refresh for other reasons
            self.root.after(0, self._update_gui_listbox)
            
        self.root.after(int(APP_INTERVAL * 1000), self._schedule_periodic_tasks)

    def _update_gui_listbox(self):
        num_total_copies = len(self.active_instances) + 1 # +1 for self
        self.count_display_var.set(str(num_total_copies))

        self.listbox.delete(0, END)
        
        display_entries = [f"{self.my_ip}:{self.my_identifier_port}"] # Self first
        for ip_addr, id_port in sorted(self.active_instances.keys()):
            display_entries.append(f"{ip_addr}:{id_port}")
        
        for entry in display_entries:
            self.listbox.insert(END, entry)
    
    def _on_closing_event(self):
        bye_message = f"BYE {self.my_identifier_port}".encode()
        try:
            for _ in range(3): 
                if hasattr(self, 'broadcast_socket') and self.broadcast_socket.fileno() != -1:
                    self.broadcast_socket.sendto(bye_message, (BCAST_IP, DISCOVERY_PORT))
                    time.sleep(0.05)
        except OSError as e:
            print(f"Ошибка отправки BYE: {e}")
        finally:
            if hasattr(self, 'broadcast_socket') and self.broadcast_socket:
                try: # Try to close gracefully
                    self.broadcast_socket.close()
                except: pass # Ignore errors on close
            self.root.destroy()

if __name__ == "__main__":
    main_tk_window = tk.Tk()
    app_instance = CopiesApp(main_tk_window)
    main_tk_window.mainloop() 