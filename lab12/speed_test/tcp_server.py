import socket
import threading
import time
import struct

class TCPServerLogic:
    def __init__(self):
        self.server_socket = None
        self.client_conn = None
        self.server_thread = None
        self._is_running = False
        self._stop_requested = False
        self.update_callback = None
        self.ip = ""
        self.port = 0
        
        self.display_received_packets = 0
        self.display_total_packets_expected = 0 
        self.display_received_bytes = 0
        self.display_speed_bps = 0
        self.current_status_message = "Инициализация"

    def is_running(self):
        return self._is_running

    def start(self, ip, port, update_callback):
        if self.is_running():
            self.log("Сервер уже запущен.")
            return

        self.ip = ip
        self.port = port
        self.update_callback = update_callback
        self._stop_requested = False
        self._is_running = True

        self.display_received_packets = 0
        self.display_total_packets_expected = 0
        self.display_received_bytes = 0
        self.display_speed_bps = 0

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen(1)
            self.log(f"Сервер слушает на {self.ip}:{self.port}")
            self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, f"Ожидание подключения на {self.ip}:{self.port}...")
        except Exception as e:
            self.log(f"Ошибка запуска сервера: {e}")
            self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, f"Ошибка: {e}")
            self._is_running = False
            return

        self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
        self.server_thread.start()

    def _server_loop(self):
        try:
            while not self._stop_requested:
                self.log("Ожидание нового подключения...")
                self.server_socket.settimeout(1.0) 
                try:
                    self.client_conn, addr = self.server_socket.accept()
                except socket.timeout:
                    continue 
                except Exception as e:
                    if self._stop_requested:
                        self.log("Сервер остановлен во время ожидания подключения.")
                        break
                    self.log(f"Ошибка приема подключения: {e}")
                    continue 
                
                self.server_socket.settimeout(None) 
                self.log(f"Подключение от {addr}")
                
                self.display_received_packets = 0
                self.display_total_packets_expected = 0 
                self.display_received_bytes = 0
                self.display_speed_bps = 0
                self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, f"Подключен: {addr}")
                
                self._handle_client()
                
                self.client_conn = None 
                if self._stop_requested: 
                    break
                self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, f"Ожидание подключения на {self.ip}:{self.port}...") 

        except Exception as e:
            if not self._stop_requested:
                self.log(f"Критическая ошибка в цикле сервера: {e}")
                self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, f"Критическая ошибка: {e}")
        finally:
            self.log("Цикл сервера завершен.")
            self._is_running = False
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            if not self._stop_requested or ("Остановка" not in self.current_status_message and "Остановлен" not in self.current_status_message) :
                 self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Остановлен")


    def _handle_client(self):
        session_bytes_received = 0
        session_packets_received = 0
        session_start_time = time.time()
        
        session_expected_packets = 0 

        try:
            metadata_header = self.client_conn.recv(8) 
            if not metadata_header or len(metadata_header) < 8:
                self.log("Не удалось получить метаданные от клиента.")
                self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Ошибка: не получены метаданные")
                return

            session_expected_packets = struct.unpack("!I", metadata_header[:4])[0]
            packet_size = struct.unpack("!I", metadata_header[4:8])[0]
            
            self.display_total_packets_expected = session_expected_packets
            self.log(f"Ожидается {session_expected_packets} пакетов размером {packet_size} байт.")
            self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Получение данных...")

            if packet_size == 0: 
                self.log("Ошибка: Размер пакета равен 0.")
                self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Ошибка: нулевой размер пакета")
                return

            while session_packets_received < session_expected_packets and not self._stop_requested:
                data_chunk = self.client_conn.recv(packet_size)
                if not data_chunk:
                    self.log("Соединение закрыто клиентом преждевременно.")
                    self.display_received_packets = session_packets_received
                    self.display_received_bytes = session_bytes_received
                    self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Ошибка: клиент закрыл соединение")
                    break 
                
                session_bytes_received += len(data_chunk)
                session_packets_received += 1
                
                elapsed_time = time.time() - session_start_time
                current_speed_bps = (session_bytes_received * 8) / elapsed_time if elapsed_time > 0 else 0
                
                self.display_received_packets = session_packets_received
                self.display_received_bytes = session_bytes_received
                self.display_speed_bps = current_speed_bps
                self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Получение данных...")
                self.log(f"Получено {session_packets_received}/{session_expected_packets} пакетов. Всего байт: {session_bytes_received}. Скорость: {current_speed_bps/(1024*1024):.2f} MB/s")

            if self._stop_requested:
                self.log("Остановка обработки клиента по запросу.")
                self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Остановлено пользователем")
            elif session_packets_received == session_expected_packets:
                self.log("Все пакеты получены успешно.")
                elapsed_time = time.time() - session_start_time
                final_speed_bps = (session_bytes_received * 8) / elapsed_time if elapsed_time > 0 else 0
                self.display_received_packets = session_packets_received
                self.display_received_bytes = session_bytes_received
                self.display_speed_bps = final_speed_bps
                self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Завершено")

        except socket.timeout:
            self.log("Тайм-аут при получении данных от клиента.")
            self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Ошибка: таймаут клиента")
        except ConnectionResetError:
            self.log("Соединение сброшено клиентом.")
            self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Ошибка: клиент сбросил соединение")
        except Exception as e:
            self.log(f"Ошибка при обработке клиента: {e}")
            self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, f"Ошибка: {e}")
        finally:
            if self.client_conn:
                try:
                    self.client_conn.close()
                except Exception as e_close:
                    self.log(f"Ошибка при закрытии сокета клиента: {e_close}")
                self.client_conn = None
            self.log("Обработка клиента завершена.")

    def stop(self):
        self.log("Запрос на остановку сервера...")
        if "Остановка" not in self.current_status_message and "Остановлен" not in self.current_status_message:
            self.current_status_message = "Остановка..."
        
        self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, self.current_status_message) 
        self._stop_requested = True
        
        if self.client_conn: 
            try:
                self.client_conn.shutdown(socket.SHUT_RDWR) 
                self.client_conn.close()
            except Exception as e:
                self.log(f"Ошибка при принудительном закрытии сокета клиента: {e}")
            self.client_conn = None

        if self.server_socket: 
            try:
                self.server_socket.close()
            except Exception as e:
                self.log(f"Ошибка при закрытии серверного сокета: {e}")

        if self.server_thread and self.server_thread.is_alive():
            self.log("Ожидание завершения потока сервера...")
            self.server_thread.join(timeout=2.0) 
            if self.server_thread.is_alive():
                self.log("Поток сервера не завершился штатно.")
        
        self._is_running = False 
        self.log("Сервер остановлен.")
        if self.update_callback and "Остановлен" not in self.current_status_message:
             self.update_gui_stats(self.display_received_packets, self.display_total_packets_expected, self.display_received_bytes, self.display_speed_bps, "Остановлен")

    def update_gui_stats(self, received_pkts, total_pkts_exp, rcv_bytes, speed, status_msg):
        self.current_status_message = status_msg
        if self.update_callback:
            self.update_callback(received_pkts, total_pkts_exp, rcv_bytes, speed, status_msg)

    def log(self, message):
        print(f"[TCPServer]: {message}") 