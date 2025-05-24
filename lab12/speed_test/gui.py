import tkinter as tk
from tkinter import ttk, messagebox
import threading

class SpeedTestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Измеритель скорости TCP/UDP")
        self.root.geometry("300x150")

        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)


        ttk.Button(main_frame, text="TCP Отправитель", command=self.open_tcp_sender).grid(row=0, column=0, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(main_frame, text="TCP Получатель", command=self.open_tcp_receiver).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        self.udp_sender_button = ttk.Button(main_frame, text="UDP Отправитель", command=self.open_udp_sender)
        self.udp_sender_button.grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)
        
        self.udp_receiver_button = ttk.Button(main_frame, text="UDP Получатель", command=self.open_udp_receiver)
        self.udp_receiver_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        self.tcp_client_instance = None
        self.tcp_server_instance = None

    def open_tcp_sender(self):
        TCPSenderWindow(self.root, self)

    def open_tcp_receiver(self):
        TCPReceiverWindow(self.root, self)

    def open_udp_sender(self):
        UDPSenderWindow(self.root, self)

    def open_udp_receiver(self):
        UDPReceiverWindow(self.root, self)

class TCPSenderWindow:
    def __init__(self, parent, app_controller):
        self.app_controller = app_controller
        self.window = tk.Toplevel(parent)
        self.window.title("Отправитель TCP")
        self.window.geometry("350x230")

        frame = ttk.Frame(self.window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="IP адрес получателя:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.ip_entry = ttk.Entry(frame, width=25)
        self.ip_entry.grid(row=0, column=1, pady=3, sticky=tk.EW)
        self.ip_entry.insert(0, "127.0.0.1")

        ttk.Label(frame, text="Порт отправки:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.port_entry = ttk.Entry(frame, width=10)
        self.port_entry.grid(row=1, column=1, pady=3, sticky=tk.W)
        self.port_entry.insert(0, "8080")

        ttk.Label(frame, text="Количество пакетов:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.packets_entry = ttk.Entry(frame, width=10)
        self.packets_entry.grid(row=2, column=1, pady=3, sticky=tk.W)
        self.packets_entry.insert(0, "10")
        
        ttk.Label(frame, text="Размер пакета (байт):").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.packet_size_entry = ttk.Entry(frame, width=10)
        self.packet_size_entry.grid(row=3, column=1, pady=3, sticky=tk.W)
        self.packet_size_entry.insert(0, "1024")

        self.send_button = ttk.Button(frame, text="Отправить", command=self.start_sending)
        self.send_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.status_var = tk.StringVar(value="Статус: Готов")
        ttk.Label(frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=3)
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_sending(self):
        ip = self.ip_entry.get()
        port_str = self.port_entry.get()
        num_packets_str = self.packets_entry.get()
        packet_size_str = self.packet_size_entry.get()

        if not all([ip, port_str, num_packets_str, packet_size_str]):
            messagebox.showerror("Ошибка", "Все поля должны быть заполнены.", parent=self.window)
            return
        try:
            port = int(port_str)
            num_packets = int(num_packets_str)
            packet_size = int(packet_size_str)
            if port <= 0 or num_packets <= 0 or packet_size <= 0:
                raise ValueError("Значения должны быть положительными.")
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректные числовые значения: {e}", parent=self.window)
            return

        self.status_var.set(f"Статус: Подготовка к отправке...")
        if self.app_controller.tcp_client_instance:
             self.app_controller.tcp_client_instance.start_transfer(ip, port, num_packets, packet_size, self.update_status_callback)
        else:
            self.update_status_callback("Клиент не инициализирован.")


    def update_status_callback(self, message):
        self.status_var.set(f"Статус: {message}")
        if "завершено" in message.lower() or "ошибка" in message.lower():
            self.send_button.config(state=tk.NORMAL)

    def on_close(self):
        if self.app_controller.tcp_client_instance and self.app_controller.tcp_client_instance.is_running():
            if messagebox.askyesno("Предупреждение", "Передача данных активна. Прервать?", parent=self.window):
                self.app_controller.tcp_client_instance.stop_transfer()
        self.window.destroy()


class TCPReceiverWindow:
    def __init__(self, parent, app_controller):
        self.app_controller = app_controller
        self.window = tk.Toplevel(parent)
        self.window.title("Получатель TCP")
        self.window.geometry("380x250")


        frame = ttk.Frame(self.window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)


        ttk.Label(frame, text="IP для прослушивания:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.ip_entry = ttk.Entry(frame, width=25)
        self.ip_entry.grid(row=0, column=1, pady=3, sticky=tk.EW)
        self.ip_entry.insert(0, "0.0.0.0")

        ttk.Label(frame, text="Порт для прослушивания:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.port_entry = ttk.Entry(frame, width=10)
        self.port_entry.grid(row=1, column=1, pady=3, sticky=tk.W)
        self.port_entry.insert(0, "8080")

        ttk.Label(frame, text="Скорость передачи:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.speed_var = tk.StringVar(value="0 B/s")
        ttk.Label(frame, textvariable=self.speed_var).grid(row=2, column=1, sticky=tk.W, pady=3)

        ttk.Label(frame, text="Получено пакетов:").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.packets_var = tk.StringVar(value="0/0")
        ttk.Label(frame, textvariable=self.packets_var).grid(row=3, column=1, sticky=tk.W, pady=3)
        
        self.bytes_var = tk.StringVar(value="0 Байт")
        ttk.Label(frame, text="Получено данных:").grid(row=4, column=0, sticky=tk.W, pady=3)
        ttk.Label(frame, textvariable=self.bytes_var).grid(row=4, column=1, sticky=tk.W, pady=3)


        self.toggle_button_var = tk.StringVar(value="Получить")
        self.toggle_button = ttk.Button(frame, textvariable=self.toggle_button_var, command=self.toggle_server)
        self.toggle_button.grid(row=5, column=0, columnspan=2, pady=10)

        self.status_var = tk.StringVar(value="Статус: Остановлен")
        ttk.Label(frame, textvariable=self.status_var).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=3)
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def toggle_server(self):
        if self.app_controller.tcp_server_instance and self.app_controller.tcp_server_instance.is_running():
            self.status_var.set("Статус: Остановка...")
            self.app_controller.tcp_server_instance.stop()
        else:
            ip = self.ip_entry.get()
            port_str = self.port_entry.get()
            if not ip or not port_str:
                messagebox.showerror("Ошибка", "IP и порт должны быть заполнены.", parent=self.window)
                return
            try:
                port = int(port_str)
                if port <= 0: raise ValueError("Порт должен быть положительным числом")
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Некорректный порт: {e}", parent=self.window)
                return
            
            self.status_var.set(f"Статус: Запуск сервера на {ip}:{port}...")
            if self.app_controller.tcp_server_instance:
                self.app_controller.tcp_server_instance.start(ip, port, self.update_server_stats_callback)
            else:
                 self.update_server_stats_callback(0,0,0,0,"Сервер не инициализирован")


    def update_server_stats_callback(self, received_packets, total_packets, received_bytes, speed_bps, status_message):
        self.packets_var.set(f"{received_packets}/{total_packets}")
        
        if received_bytes < 1024:
            self.bytes_var.set(f"{received_bytes} Байт")
        elif received_bytes < 1024*1024:
            self.bytes_var.set(f"{received_bytes/1024:.2f} КБайт")
        else:
            self.bytes_var.set(f"{received_bytes/(1024*1024):.2f} МБайт")

        if speed_bps < 1024:
            self.speed_var.set(f"{speed_bps:.2f} B/s")
        elif speed_bps < 1024 * 1024:
            self.speed_var.set(f"{speed_bps/1024:.2f} KB/s")
        else:
            self.speed_var.set(f"{speed_bps/(1024*1024):.2f} MB/s")
        
        self.status_var.set(f"Статус: {status_message}")

        if "работает" in status_message.lower() or "ожидание" in status_message.lower() :
            self.toggle_button_var.set("Остановить")
            self.ip_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
        else:
            self.toggle_button_var.set("Получить")
            self.ip_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)

    def on_close(self):
        if self.app_controller.tcp_server_instance and self.app_controller.tcp_server_instance.is_running():
             self.app_controller.tcp_server_instance.stop()
        self.window.destroy()

class UDPSenderWindow:
    def __init__(self, parent, app_controller):
        self.app_controller = app_controller
        self.window = tk.Toplevel(parent)
        self.window.title("Отправитель UDP")
        self.window.geometry("350x230")

        frame = ttk.Frame(self.window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="IP адрес получателя:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.ip_entry = ttk.Entry(frame, width=25)
        self.ip_entry.grid(row=0, column=1, pady=3, sticky=tk.EW)
        self.ip_entry.insert(0, "127.0.0.1")

        ttk.Label(frame, text="Порт отправки:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.port_entry = ttk.Entry(frame, width=10)
        self.port_entry.grid(row=1, column=1, pady=3, sticky=tk.W)
        self.port_entry.insert(0, "8888")

        ttk.Label(frame, text="Количество пакетов:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.packets_entry = ttk.Entry(frame, width=10)
        self.packets_entry.grid(row=2, column=1, pady=3, sticky=tk.W)
        self.packets_entry.insert(0, "100")
        
        ttk.Label(frame, text="Размер пакета (байт):").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.packet_size_entry = ttk.Entry(frame, width=10)
        self.packet_size_entry.grid(row=3, column=1, pady=3, sticky=tk.W)
        self.packet_size_entry.insert(0, "1024")

        self.send_button = ttk.Button(frame, text="Отправить", command=self.start_sending)
        self.send_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.status_var = tk.StringVar(value="Статус: Готов")
        ttk.Label(frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=3)
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_sending(self):
        ip = self.ip_entry.get()
        port_str = self.port_entry.get()
        num_packets_str = self.packets_entry.get()
        packet_size_str = self.packet_size_entry.get()

        if not all([ip, port_str, num_packets_str, packet_size_str]):
            messagebox.showerror("Ошибка", "Все поля должны быть заполнены.", parent=self.window)
            return
        try:
            port = int(port_str)
            num_packets = int(num_packets_str)
            packet_size = int(packet_size_str)
            if port <= 0 or num_packets <= 0 or packet_size <= 0:
                raise ValueError("Значения должны быть положительными.")
            if packet_size > 1472:
                messagebox.showwarning("Предупреждение", f"Размер пакета {packet_size} байт может быть слишком большим для одной UDP датаграммы (рекомендуется <= 1472).", parent=self.window)
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректные числовые значения: {e}", parent=self.window)
            return

        self.status_var.set(f"Статус: Подготовка к отправке UDP...")
        self.send_button.config(state=tk.DISABLED)
        if self.app_controller.udp_client_instance:
             self.app_controller.udp_client_instance.start_transfer(ip, port, num_packets, packet_size, self.update_status_callback)
        else:
            self.update_status_callback("UDP Клиент не инициализирован.")
            self.send_button.config(state=tk.NORMAL)

    def update_status_callback(self, message):
        self.status_var.set(f"Статус: {message}")
        if "завершено" in message.lower() or "ошибка" in message.lower() or "готов" in message.lower() or "прервана" in message.lower():
            self.send_button.config(state=tk.NORMAL)

    def on_close(self):
        if self.app_controller.udp_client_instance and self.app_controller.udp_client_instance.is_running():
            if messagebox.askyesno("Предупреждение", "Передача данных активна. Прервать?", parent=self.window):
                self.app_controller.udp_client_instance.stop_transfer()
            else:
                return
        self.window.destroy()


class UDPReceiverWindow:
    def __init__(self, parent, app_controller):
        self.app_controller = app_controller 
        self.window = tk.Toplevel(parent)
        self.window.title("Получатель UDP")
        self.window.geometry("380x280")

        frame = ttk.Frame(self.window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="IP для прослушивания:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.ip_entry = ttk.Entry(frame, width=25)
        self.ip_entry.grid(row=0, column=1, pady=3, sticky=tk.EW)
        self.ip_entry.insert(0, "0.0.0.0")

        ttk.Label(frame, text="Порт для прослушивания:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.port_entry = ttk.Entry(frame, width=10)
        self.port_entry.grid(row=1, column=1, pady=3, sticky=tk.W)
        self.port_entry.insert(0, "8888")

        ttk.Label(frame, text="Скорость передачи:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.speed_var = tk.StringVar(value="0 B/s")
        ttk.Label(frame, textvariable=self.speed_var).grid(row=2, column=1, sticky=tk.W, pady=3)

        ttk.Label(frame, text="Получено пакетов:").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.packets_var = tk.StringVar(value="0/0")
        ttk.Label(frame, textvariable=self.packets_var).grid(row=3, column=1, sticky=tk.W, pady=3)
        
        ttk.Label(frame, text="Потеряно пакетов:").grid(row=4, column=0, sticky=tk.W, pady=3)
        self.lost_packets_var = tk.StringVar(value="0 (0.00%)")
        ttk.Label(frame, textvariable=self.lost_packets_var).grid(row=4, column=1, sticky=tk.W, pady=3)

        ttk.Label(frame, text="Получено данных:").grid(row=5, column=0, sticky=tk.W, pady=3)
        self.bytes_var = tk.StringVar(value="0 Байт")
        ttk.Label(frame, textvariable=self.bytes_var).grid(row=5, column=1, sticky=tk.W, pady=3)

        self.toggle_button_var = tk.StringVar(value="Получить")
        self.toggle_button = ttk.Button(frame, textvariable=self.toggle_button_var, command=self.toggle_server)
        self.toggle_button.grid(row=6, column=0, columnspan=2, pady=10)

        self.status_var = tk.StringVar(value="Статус: Остановлен")
        ttk.Label(frame, textvariable=self.status_var).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=3)
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def toggle_server(self):
        if self.app_controller.udp_server_instance and self.app_controller.udp_server_instance.is_running():
            self.status_var.set("Статус: Остановка UDP сервера...")
            self.app_controller.udp_server_instance.stop()
        else:
            ip = self.ip_entry.get()
            port_str = self.port_entry.get()
            if not ip or not port_str:
                messagebox.showerror("Ошибка", "IP и порт должны быть заполнены.", parent=self.window)
                return
            try:
                port = int(port_str)
                if port <= 0: raise ValueError("Порт должен быть положительным числом")
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Некорректный порт: {e}", parent=self.window)
                return
            
            self.status_var.set(f"Статус: Запуск UDP сервера на {ip}:{port}...")
            if self.app_controller.udp_server_instance:
                self.app_controller.udp_server_instance.start(ip, port, self.update_server_stats_callback)
            else:
                 self.update_server_stats_callback(0,0,0,0,0, "UDP Сервер не инициализирован")

    def update_server_stats_callback(self, received_pkts, total_pkts_exp, lost_pkts, received_bytes, speed_bps, status_message):
        self.packets_var.set(f"{received_pkts}/{total_pkts_exp}")
        
        if total_pkts_exp > 0:
            loss_percentage = (lost_pkts / total_pkts_exp) * 100 if total_pkts_exp > 0 else 0
            self.lost_packets_var.set(f"{lost_pkts} ({loss_percentage:.2f}%)")
        else:
            self.lost_packets_var.set(f"{lost_pkts}")

        if received_bytes < 1024:
            self.bytes_var.set(f"{received_bytes} Байт")
        elif received_bytes < 1024*1024:
            self.bytes_var.set(f"{received_bytes/1024:.2f} КБайт")
        else:
            self.bytes_var.set(f"{received_bytes/(1024*1024):.2f} МБайт")

        if speed_bps < 1024:
            self.speed_var.set(f"{speed_bps:.2f} B/s")
        elif speed_bps < 1024 * 1024:
            self.speed_var.set(f"{speed_bps/1024:.2f} KB/s")
        else:
            self.speed_var.set(f"{speed_bps/(1024*1024):.2f} MB/s")
        
        self.status_var.set(f"Статус: {status_message}")

        if "работает" in status_message.lower() or "ожидание" in status_message.lower() or "получение" in status_message.lower():
            self.toggle_button_var.set("Остановить")
            self.ip_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
        else: 
            self.toggle_button_var.set("Получить")
            self.ip_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)

    def on_close(self):
        if self.app_controller.udp_server_instance and self.app_controller.udp_server_instance.is_running():
            self.app_controller.udp_server_instance.stop()
        self.window.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = SpeedTestGUI(root)
    
    from tcp_server import TCPServerLogic
    from tcp_client import TCPClientLogic
    app.tcp_server_instance = TCPServerLogic()
    app.tcp_client_instance = TCPClientLogic()

    from udp_server import UDPServerLogic
    from udp_client import UDPClientLogic
    app.udp_server_instance = UDPServerLogic()
    app.udp_client_instance = UDPClientLogic()
    
    root.mainloop() 