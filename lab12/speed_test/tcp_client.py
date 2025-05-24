import socket
import threading
import time
import os
import struct

class TCPClientLogic:
    def __init__(self):
        self.client_socket = None
        self.client_thread = None
        self._is_running = False
        self._stop_requested = False
        self.update_callback = None

    def is_running(self):
        return self._is_running

    def start_transfer(self, ip, port, num_packets, packet_size, update_callback):
        if self.is_running():
            self.log("Передача уже активна.")
            if self.update_callback:
                 self.update_callback("Ошибка: Передача уже запущена")
            return

        self.ip = ip
        self.port = port
        self.num_packets = num_packets
        self.packet_size = packet_size
        self.update_callback = update_callback
        self._stop_requested = False
        self._is_running = True
        
        self.update_gui_status(f"Подключение к {self.ip}:{self.port}...")
        self.client_thread = threading.Thread(target=self._transfer_loop, daemon=True)
        self.client_thread.start()

    def _transfer_loop(self):
        packets_sent_count = 0
        total_bytes_sent = 0
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.ip, self.port))
            self.log(f"Подключено к серверу {self.ip}:{self.port}")

            metadata_header = struct.pack("!II", self.num_packets, self.packet_size)
            self.client_socket.sendall(metadata_header)
            self.log(f"Отправлены метаданные: {self.num_packets} пакетов, размер {self.packet_size} байт.")
            self.update_gui_status(f"Отправка 0/{self.num_packets}...")

            for i in range(self.num_packets):
                if self._stop_requested:
                    self.log("Остановка передачи по запросу.")
                    self.update_gui_status("Передача прервана пользователем")
                    break

                payload = os.urandom(self.packet_size)
                self.client_socket.sendall(payload)
                
                packets_sent_count += 1
                total_bytes_sent += len(payload)
                self.log(f"Отправлен пакет {packets_sent_count}/{self.num_packets} ({len(payload)} байт)")
                self.update_gui_status(f"Отправлено {packets_sent_count}/{self.num_packets}")

            if not self._stop_requested:
                if packets_sent_count == self.num_packets:
                    self.log("Все пакеты успешно отправлены.")
                    self.update_gui_status(f"Завершено: {packets_sent_count}/{self.num_packets} пакетов ({total_bytes_sent} байт)")
                else:
                    self.log(f"Отправка завершилась неполностью: {packets_sent_count}/{self.num_packets}")
                    self.update_gui_status(f"Ошибка: отправлено {packets_sent_count}/{self.num_packets}")
            
        except socket.gaierror as e:
            self.log(f"Ошибка адреса/подключения: {e}")
            self.update_gui_status(f"Ошибка адреса: {e}")
        except ConnectionRefusedError:
            self.log(f"Ошибка подключения: сервер {self.ip}:{self.port} не найден или отказал в соединении.")
            self.update_gui_status(f"Ошибка: сервер не отвечает ({self.ip}:{self.port})")
        except socket.error as e:
            if self._stop_requested:
                 self.log(f"Сокет закрыт во время остановки: {e}")
                 self.update_gui_status("Передача прервана")
            else:
                self.log(f"Ошибка сокета: {e}")
                self.update_gui_status(f"Ошибка сокета: {e}")
        except Exception as e:
            self.log(f"Непредвиденная ошибка при передаче: {e}")
            self.update_gui_status(f"Ошибка: {e}")
        finally:
            if self.client_socket:
                try:
                    self.client_socket.close()
                except Exception as e_close:
                    self.log(f"Ошибка при закрытии сокета клиента: {e_close}")
                self.client_socket = None
            self._is_running = False
            self.log("Передача данных завершена (или прервана).")
            current_status = self.get_current_status_from_gui_somehow_or_assume()
            if self.update_callback and not ("Завершено" in current_status or "прервана" in current_status or "Ошибка" in current_status):
                if self._stop_requested:
                    self.update_gui_status("Передача прервана") 


    def stop_transfer(self):
        self.log("Запрос на остановку передачи...")
        self._stop_requested = True
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR) 
                self.client_socket.close()
            except Exception as e:
                self.log(f"Ошибка при закрытии сокета во время остановки: {e}")
        
        if self.client_thread and self.client_thread.is_alive():
            self.log("Ожидание завершения потока клиента...")
            self.client_thread.join(timeout=2.0)
            if self.client_thread.is_alive():
                self.log("Поток клиента не завершился штатно.")
        
        self._is_running = False
        if self.update_callback:
            self.update_callback("Готов (остановлено)") 
        self.log("Передача остановлена.")

    def update_gui_status(self, message):
        if self.update_callback:
            self.update_callback(message)

    def log(self, message):
        print(f"[TCPClient]: {message}")
        
    def get_current_status_from_gui_somehow_or_assume(self):
        return "" 