import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import queue
import socket

class TranslatorGUI:
    def __init__(self, root, core_logic):
        self.root = root
        self.core_logic = core_logic
        self.root.title("Транслятор портов")
        self.root.geometry("850x650")

        top_controls_frame = ttk.Frame(root, padding="5")
        top_controls_frame.pack(fill=tk.X, pady=5, padx=5)

        rules_table_frame = ttk.LabelFrame(root, text="Правила трансляции", padding="10")
        rules_table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        log_display_frame = ttk.LabelFrame(root, text="Логи", padding="10")
        log_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        manage_frame = ttk.LabelFrame(top_controls_frame, text="Управление")
        manage_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)

        ttk.Label(manage_frame, text="IP адрес (локальный): ").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.local_ip_entry = ttk.Entry(manage_frame, width=15)
        self.local_ip_entry.grid(row=0, column=1, padx=5, pady=5)
        self.local_ip_entry.insert(0, "127.0.0.1")

        self.start_button = ttk.Button(manage_frame, text="Запустить транслятор", command=self.start_translator)
        self.start_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        self.stop_button = ttk.Button(manage_frame, text="Остановить транслятор", command=self.stop_translator, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        self.reload_button = ttk.Button(manage_frame, text="Перезагрузить конфиг", command=self.reload_config)
        self.reload_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        resolve_frame = ttk.LabelFrame(top_controls_frame, text="Получение IP")
        resolve_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.Y)

        ttk.Label(resolve_frame, text="Имя хоста:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.hostname_entry = ttk.Entry(resolve_frame, width=20)
        self.hostname_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(resolve_frame, text="IP адрес:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.resolved_ip_entry = ttk.Entry(resolve_frame, width=20, state="readonly")
        self.resolved_ip_entry.grid(row=1, column=1, padx=5, pady=5)
        
        self.resolve_button = ttk.Button(resolve_frame, text="Получить", command=self.resolve_ip)
        self.resolve_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        self.rules_tree = ttk.Treeview(
            rules_table_frame, 
            columns=("name", "listen_ip", "listen_port", "target_ip_display", "target_port"),
            show="headings"
        )
        self.rules_tree.heading("name", text="Название")
        self.rules_tree.heading("listen_ip", text="Внутренний IP")
        self.rules_tree.heading("listen_port", text="Внутренний порт")
        self.rules_tree.heading("target_ip_display", text="Внешний IP")
        self.rules_tree.heading("target_port", text="Внешний порт")

        self.rules_tree.column("name", width=120, anchor=tk.W)
        self.rules_tree.column("listen_ip", width=100, anchor=tk.W)
        self.rules_tree.column("listen_port", width=100, anchor=tk.CENTER)
        self.rules_tree.column("target_ip_display", width=150, anchor=tk.W)
        self.rules_tree.column("target_port", width=100, anchor=tk.CENTER)
        
        self.rules_tree.pack(fill=tk.BOTH, expand=True)
        self.load_rules_to_gui()

        self.log_text_widget = scrolledtext.ScrolledText(log_display_frame, height=10, state=tk.DISABLED)
        self.log_text_widget.pack(fill=tk.BOTH, expand=True)
        
        self.process_log_queue()

    def resolve_ip(self):
        hostname = self.hostname_entry.get()
        if not hostname:
            self.core_logic._log("Ошибка: Имя хоста не может быть пустым для DNS разрешения.") 
            return
        try:
            ip_address = socket.gethostbyname(hostname)
            self.resolved_ip_entry.config(state=tk.NORMAL)
            self.resolved_ip_entry.delete(0, tk.END)
            self.resolved_ip_entry.insert(0, ip_address)
            self.resolved_ip_entry.config(state="readonly")
            self.core_logic._log(f"Хост {hostname} разрешен в {ip_address}")
        except socket.gaierror:
            self.core_logic._log(f"Ошибка: Не удалось разрешить имя хоста '{hostname}'")
            messagebox.showerror("Ошибка разрешения", f"Не удалось разрешить имя хоста: {hostname}", parent=self.root)

    def load_rules_to_gui(self):
        for i in self.rules_tree.get_children():
            self.rules_tree.delete(i)
        
        rules = self.core_logic.get_rules() 
        for rule in rules:
            target_host = rule.get("target_host", "")
            display_target_ip = target_host
            if target_host:
                try:
                    display_target_ip = socket.gethostbyname(target_host)
                except socket.gaierror:
                    display_target_ip = f"{target_host} (не удалось разрешить)" 
                    self.core_logic._log(f"GUI: Не удалось разрешить '{target_host}' для отображения в таблице.")
                except Exception as e:
                    display_target_ip = f"{target_host} (ошибка: {e})"
                    self.core_logic._log(f"GUI: Ошибка при разрешении '{target_host}': {e}")

            self.rules_tree.insert("", tk.END, values=(
                rule.get("name", ""),
                rule.get("listen_ip", ""),
                rule.get("listen_port", ""),
                display_target_ip,
                rule.get("target_port", "")
            ))
        self.core_logic._log("Правила отображены в GUI.") 

    def start_translator(self):
        self.core_logic._log("Попытка запуска транслятора через GUI...")
        if self.core_logic.start_translator(): 
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.reload_button.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Ошибка", "Не удалось запустить транслятор. Смотрите логи.", parent=self.root)

    def stop_translator(self):
        self.core_logic._log("Попытка остановки транслятора через GUI...")
        self.core_logic.stop_translator()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.reload_button.config(state=tk.NORMAL)

    def reload_config(self):
        self.core_logic._log("Перезагрузка конфигурации через GUI...")
        if self.core_logic.reload_rules_from_file():
            self.load_rules_to_gui() 
        else:
            messagebox.showerror("Ошибка перезагрузки", "Не удалось перезагрузить правила. Смотрите логи для подробностей.", parent=self.root)

    def _display_log_message(self, message):
        self.log_text_widget.config(state=tk.NORMAL)
        self.log_text_widget.insert(tk.END, message + "\n")
        self.log_text_widget.config(state=tk.DISABLED)
        self.log_text_widget.see(tk.END)

    def process_log_queue(self):
        try:
            while True: 
                message = self.core_logic.log_queue.get_nowait()
                self._display_log_message(message)
                self.root.update_idletasks() 
        except queue.Empty:
            pass 
        finally:
            self.root.after(100, self.process_log_queue) 

if __name__ == '__main__':
    class MockCoreLogic:
        def __init__(self):
            self.log_queue = queue.Queue()
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_file = os.path.join(base_dir, "port_rules.json")
            self.rules = []
            self.load_rules_from_file()

        def _log(self, message):
            print(f"[MockCore]: {message}")
            self.log_queue.put(message)

        def get_rules(self):
            return self.rules

        def load_rules_from_file(self):
            self._log(f"MockCore: Loading rules from {self.config_file}")
            try:
                with open(self.config_file, 'r') as f:
                    self.rules = json.load(f)
                self._log(f"MockCore: Loaded {len(self.rules)} rules.")
                return True
            except FileNotFoundError:
                self._log(f"MockCore: Error - Config file {self.config_file} not found.")
                self.rules = []
                return False
            except json.JSONDecodeError:
                self._log(f"MockCore: Error - Could not decode JSON from {self.config_file}.")
                self.rules = []
                return False
        
        def reload_rules_from_file(self):
            self._log("MockCore: Reload rules called")
            return self.load_rules_from_file()

        def start_translator(self):
            self._log("MockCore: Start Translator called")
            if not self.rules:
                self._log("MockCore: No rules to start.")
                return False
            self._log("MockCore: Translator started (mock)")
            return True 

        def stop_translator(self):
            self._log("MockCore: Stop Translator called")

    root = tk.Tk()
    mock_core = MockCoreLogic()
    app = TranslatorGUI(root, mock_core)
    root.mainloop() 