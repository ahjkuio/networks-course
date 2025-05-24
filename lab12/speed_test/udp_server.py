import socket
import threading
import time
import struct

MSG_TYPE_METADATA = 0 
MSG_TYPE_DATA = 1
MSG_TYPE_ACK_METADATA = 2
MSG_TYPE_FIN = 3
MSG_TYPE_STATS_REQUEST = 4

DATA_TIMEOUT_SECONDS = 5 
IDLE_RECV_TIMEOUT_SECONDS = 1

class UDPServerLogic:
    def __init__(self):
        self.server_socket = None
        self.server_thread = None
        self._is_running = False
        self._stop_requested = False
        self.update_callback = None
        self.ip = ""
        self.port = 0

        self.display_received_packets = 0
        self.display_total_packets_expected = 0
        self.display_lost_packets = 0
        self.display_received_bytes = 0
        self.display_speed_bps = 0
        self.current_status_message = "Инициализация"

        self.active_session_addr = None
        self.session_expected_packets = 0
        self.session_packet_size = 0
        self.session_received_seq_numbers = set()
        self.session_bytes_received = 0
        self.session_start_time = 0
        self.last_packet_time = 0

    def is_running(self):
        return self._is_running

    def start(self, ip, port, update_callback):
        if self.is_running():
            self.log("UDP Сервер уже запущен.")
            return

        self.ip = ip
        self.port = port
        self.update_callback = update_callback
        self._stop_requested = False
        self._is_running = True

        self._reset_display_stats(is_starting=True)

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.ip, self.port))
            self.log(f"UDP Сервер слушает на {self.ip}:{self.port}")
            self.update_gui_stats(f"Ожидание метаданных на {self.ip}:{self.port}...")
        except Exception as e:
            self.log(f"Ошибка запуска UDP сервера: {e}")
            self.update_gui_stats(f"Ошибка: {e}")
            self._is_running = False
            return

        self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
        self.server_thread.start()
        
    def _reset_display_stats(self, is_starting=False):
        self.display_received_packets = 0
        self.display_total_packets_expected = 0 
        self.display_lost_packets = 0
        self.display_received_bytes = 0
        self.display_speed_bps = 0
        if is_starting:
            self.current_status_message = "Остановлен"
            
    def _reset_session_state(self):
        self.active_session_addr = None
        self.session_expected_packets = 0
        self.session_packet_size = 0
        self.session_received_seq_numbers = set()
        self.session_bytes_received = 0
        self.session_start_time = 0
        self.last_packet_time = 0

    def _server_loop(self):
        buffer_size = 2048
        try:
            while not self._stop_requested:
                try:
                    if self.active_session_addr:
                        remaining_time = DATA_TIMEOUT_SECONDS - (time.time() - self.last_packet_time)
                        if remaining_time <= 0:
                            self.log(f"Таймаут сессии для {self.active_session_addr}. Завершение.")
                            self._finalize_session(status_message="Таймаут сессии")
                            continue
                        self.server_socket.settimeout(max(0.1, remaining_time))
                    else:
                        self.server_socket.settimeout(IDLE_RECV_TIMEOUT_SECONDS)
                    
                    data, addr = self.server_socket.recvfrom(buffer_size)
                    self.last_packet_time = time.time()

                    if not data:
                        continue

                    msg_type = data[0]

                    if self.active_session_addr and self.active_session_addr != addr:
                        self.log(f"Получены данные от {addr}, но активна сессия с {self.active_session_addr}. Игнорируем.")
                        continue

                    if msg_type == MSG_TYPE_METADATA:
                        if self.active_session_addr and self.active_session_addr == addr:
                            self.log(f"Получены повторные метаданные от {addr}. Перезапуск сессии.")
                        self._reset_session_state() 
                        self._reset_display_stats()
                        self.active_session_addr = addr
                        self._handle_metadata(data, addr)
                        self.last_packet_time = time.time()
                    elif msg_type == MSG_TYPE_DATA and self.active_session_addr == addr:
                        self._handle_data_packet(data, addr)
                        if self.session_received_seq_numbers and len(self.session_received_seq_numbers) >= self.session_expected_packets:
                            self.log(f"Все ожидаемые пакеты ({self.session_expected_packets}) получены от {addr}. Завершение сессии.")
                            self._finalize_session(status_message="Завершено (все пакеты)")
                    elif msg_type == MSG_TYPE_FIN and self.active_session_addr == addr:
                        self.log(f"Получен FIN от {addr}. Завершение сессии.")
                        self._finalize_session(status_message="Завершено (FIN от клиента)")
                    else:
                        self.log(f"Неизвестный тип сообщения {msg_type} или от неожиданного адреса {addr}. Данные: {data[:20]}")

                except socket.timeout:
                    if self.active_session_addr:
                        self.log(f"Таймаут ожидания данных от {self.active_session_addr}. Проверка и возможное завершение.")
                        if time.time() - self.last_packet_time > DATA_TIMEOUT_SECONDS:
                             self.log(f"Финальный таймаут сессии для {self.active_session_addr}. Завершение.")
                             self._finalize_session(status_message="Таймаут сессии (финальный)")
                    continue
                except Exception as e:
                    if self._stop_requested:
                        break
                    self.log(f"Ошибка в цикле UDP сервера: {e}")
                    if self.active_session_addr:
                        self._finalize_session(status_message=f"Ошибка: {e}")
                    else:
                        self.update_gui_stats(f"Ошибка: {e}")
        finally:
            self.log("Цикл UDP сервера завершен.")
            self._is_running = False
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            status_on_stop = "Остановлен"
            if self.current_status_message and "Ошибка" in self.current_status_message :
                status_on_stop = self.current_status_message
            elif self._stop_requested and self.active_session_addr:
                status_on_stop = "Остановлено пользователем"
            self._finalize_session(status_message=status_on_stop, is_stopping_server=True) 

    def _handle_metadata(self, data, addr):
        try:
            _, total_packets, packet_size_val = struct.unpack("!BII", data[:9])
            self.session_expected_packets = total_packets
            self.session_packet_size = packet_size_val
            self.session_start_time = time.time()
            self.log(f"Метаданные от {addr}: ожидается {self.session_expected_packets} пакетов, размер данных {self.session_packet_size} байт.")
            
            self.display_total_packets_expected = self.session_expected_packets
            self.update_gui_stats(f"Получение данных от {addr} (0/{self.session_expected_packets})")

        except struct.error as e:
            self.log(f"Ошибка распаковки метаданных от {addr}: {e}")
            self._reset_session_state()
            self.update_gui_stats(f"Ошибка метаданных от {addr}")

    def _handle_data_packet(self, data, addr):
        try:
            header_size = 5 
            _, seq_num = struct.unpack("!BI", data[:header_size])
            payload = data[header_size:]
            
            if seq_num not in self.session_received_seq_numbers:
                self.session_received_seq_numbers.add(seq_num)
                self.session_bytes_received += len(payload)
                self.display_received_packets = len(self.session_received_seq_numbers)
                self.display_received_bytes = self.session_bytes_received
            else:
                self.log(f"Получен дубликат пакета {seq_num} от {addr}. Игнорируем.")
                return

            elapsed_time = time.time() - self.session_start_time
            current_speed_bps = (self.session_bytes_received * 8) / elapsed_time if elapsed_time > 0 else 0
            self.display_speed_bps = current_speed_bps
            
            max_received_seq = 0
            if self.session_received_seq_numbers:
                 max_received_seq = max(self.session_received_seq_numbers)
            
            self.display_lost_packets = (max(0, max_received_seq + 1) - len(self.session_received_seq_numbers)) if len(self.session_received_seq_numbers) > 0 else 0
            
            self.update_gui_stats(f"Получение: {self.display_received_packets}/{self.session_expected_packets}, Потеряно: ~{self.display_lost_packets}")
            self.log(f"Пакет {seq_num} ({len(payload)} байт) от {addr}. Всего получено: {self.display_received_packets}. Байт: {self.display_received_bytes}")

        except struct.error as e:
            self.log(f"Ошибка распаковки пакета данных от {addr}: {e}")
        except Exception as e_gen:
            self.log(f"Общая ошибка при обработке пакета данных: {e_gen}")

    def _finalize_session(self, status_message="Завершено", is_stopping_server=False):
        if self.active_session_addr or is_stopping_server:
            if self.session_expected_packets > 0:
                lost_count = self.session_expected_packets - len(self.session_received_seq_numbers)
                self.display_lost_packets = max(0, lost_count)
                self.display_received_packets = len(self.session_received_seq_numbers)
                self.display_received_bytes = self.session_bytes_received
                if "Таймаут" in status_message and self.session_start_time > 0:
                    elapsed_final = time.time() - self.session_start_time
                    self.display_speed_bps = (self.session_bytes_received * 8) / elapsed_final if elapsed_final > 0 else 0
            else:
                pass
            
            self.log(f"Сессия с {self.active_session_addr if self.active_session_addr else 'N/A'} завершена. Статус: {status_message}. Потеряно: {self.display_lost_packets}")
            self.update_gui_stats(status_message)
            
            if not is_stopping_server:
                self._reset_session_state()
                self.update_gui_stats(f"Ожидание метаданных на {self.ip}:{self.port}...")
        elif not is_stopping_server:
             self.update_gui_stats(status_message)


    def stop(self):
        self.log("Запрос на остановку UDP сервера...")
        self._stop_requested = True
        self.update_gui_stats("Остановка...") 

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=max(IDLE_RECV_TIMEOUT_SECONDS, 0.5) + 0.5)
            if self.server_thread.is_alive():
                self.log("Поток UDP сервера не завершился штатно (возможно, из-за блокирующего recvfrom).")
        
        self._is_running = False
        self.log("UDP Сервер остановлен.")
        if self.update_callback and "Остановлен" not in self.current_status_message:
            if self.active_session_addr :
                 self.update_gui_stats("Остановлено пользователем")
            else:
                 self.update_gui_stats("Остановлен")


    def update_gui_stats(self, status_msg_override=None):
        final_status = status_msg_override if status_msg_override is not None else self.current_status_message
        self.current_status_message = final_status

        if self.update_callback:
            self.update_callback(
                self.display_received_packets,
                self.display_total_packets_expected,
                self.display_lost_packets,
                self.display_received_bytes,
                self.display_speed_bps,
                self.current_status_message
            )

    def log(self, message):
        print(f"[UDPServer]: {message}") 