import socket
import threading
import time
import os
import struct

MSG_TYPE_METADATA = 0
MSG_TYPE_DATA = 1
MSG_TYPE_FIN = 3

INTER_PACKET_DELAY = 0.0001

class UDPClientLogic:
    def __init__(self):
        self.client_socket = None
        self.client_thread = None
        self._is_running = False
        self._stop_requested = False
        self.update_callback = None
        self.server_ip = ""
        self.server_port = 0
        self.num_packets = 0
        self.packet_payload_size = 0

    def is_running(self):
        return self._is_running

    def start_transfer(self, ip, port, num_packets, packet_size, update_callback):
        if self.is_running():
            self.log("UDP Передача уже активна.")
            if self.update_callback:
                 self.update_callback("Ошибка: Передача уже запущена")
            return

        self.server_ip = ip
        self.server_port = port
        self.num_packets = num_packets
        self.packet_payload_size = packet_size
        self.update_callback = update_callback
        self._stop_requested = False
        self._is_running = True
        
        self.update_gui_status(f"Подготовка к отправке UDP на {self.server_ip}:{self.server_port}...")
        self.client_thread = threading.Thread(target=self._transfer_loop, daemon=True)
        self.client_thread.start()

    def _transfer_loop(self):
        packets_sent_count = 0
        total_bytes_payload_sent = 0
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.log(f"UDP Клиент создан. Цель: {self.server_ip}:{self.server_port}")

            metadata_datagram = struct.pack("!BII", MSG_TYPE_METADATA, self.num_packets, self.packet_payload_size)
            self.client_socket.sendto(metadata_datagram, (self.server_ip, self.server_port))
            self.log(f"Отправлены метаданные: {self.num_packets} пакетов, размер полезной нагрузки {self.packet_payload_size} байт.")
            self.update_gui_status(f"Отправка 0/{self.num_packets}...")

            last_sent_seq_num = -1
            for seq_num in range(self.num_packets):
                if self._stop_requested:
                    self.log("Остановка передачи UDP по запросу.")
                    self.update_gui_status("Передача прервана пользователем")
                    break

                payload = os.urandom(self.packet_payload_size)
                data_header = struct.pack("!BI", MSG_TYPE_DATA, seq_num)
                packet_datagram = data_header + payload
                
                self.client_socket.sendto(packet_datagram, (self.server_ip, self.server_port))
                
                packets_sent_count += 1
                total_bytes_payload_sent += len(payload)
                last_sent_seq_num = seq_num
                self.log(f"Отправлен UDP пакет {seq_num} ({len(payload)} байт полезной нагрузки)")
                if packets_sent_count % 10 == 0 or packets_sent_count == self.num_packets:
                    self.update_gui_status(f"Отправлено {packets_sent_count}/{self.num_packets}")
                
                if INTER_PACKET_DELAY > 0:
                    time.sleep(INTER_PACKET_DELAY)

            if not self._stop_requested or (self._stop_requested and packets_sent_count > 0):

                self.log(f"Отправка FIN пакета. Последний отправленный seq_num: {last_sent_seq_num}")
                fin_datagram = struct.pack("!BI", MSG_TYPE_FIN, last_sent_seq_num if last_sent_seq_num != -1 else 0)
                self.client_socket.sendto(fin_datagram, (self.server_ip, self.server_port))

            if not self._stop_requested:
                if packets_sent_count == self.num_packets:
                    self.log("Все UDP пакеты успешно отправлены (или, по крайней мере, попытка отправки сделана).")
                    self.update_gui_status(f"Завершено: {packets_sent_count}/{self.num_packets} ({total_bytes_payload_sent} байт полезной нагрузки)")
                else:
                    self.log(f"UDP Отправка завершилась неполностью: {packets_sent_count}/{self.num_packets}")
                    self.update_gui_status(f"Ошибка/Прервано: отправлено {packets_sent_count}/{self.num_packets}")
            
        except socket.gaierror as e: 
            self.log(f"Ошибка адреса (UDP): {e}")
            self.update_gui_status(f"Ошибка адреса: {e}")
        except socket.error as e: 
            if self._stop_requested:
                 self.log(f"Сокет UDP закрыт во время остановки: {e}")
                 self.update_gui_status("Передача прервана")
            else:
                self.log(f"Ошибка сокета UDP: {e}")
                self.update_gui_status(f"Ошибка сокета: {e}")
        except Exception as e:
            self.log(f"Непредвиденная ошибка при передаче UDP: {e}")
            self.update_gui_status(f"Ошибка: {e}")
        finally:
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            self._is_running = False
            self.log("UDP Передача данных завершена/прервана со стороны клиента.")
            final_status = self.current_gui_status_message if hasattr(self, 'current_gui_status_message') else ""
            if not ("Завершено" in final_status or "прервана" in final_status or "Ошибка" in final_status):
                if self._stop_requested:
                    self.update_gui_status("Передача прервана") 
                else: 
                    self.update_gui_status("Готов (статус неясен)")
            
    def stop_transfer(self):
        self.log("Запрос на остановку UDP передачи...")
        self._stop_requested = True
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None

        if self.client_thread and self.client_thread.is_alive():
            self.log("Ожидание завершения потока UDP клиента...")
            self.client_thread.join(timeout=1.0)
            if self.client_thread.is_alive():
                self.log("Поток UDP клиента не завершился штатно.")
        
        self._is_running = False
        if self.update_callback:
            self.update_callback("Готов (остановлено)") 
        self.log("UDP Передача остановлена.")

    def update_gui_status(self, message):
        self.current_gui_status_message = message
        if self.update_callback:
            self.update_callback(message)

    def log(self, message):
        print(f"[UDPClient]: {message}") 