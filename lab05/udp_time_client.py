#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import sys

LISTEN_HOST = '0.0.0.0' 
PORT = 12346
BUFFER_SIZE = 1024

def run_udp_time_client():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) 
        
        try:
            s.bind((LISTEN_HOST, PORT))
        except socket.error as e:
            print(f"Ошибка привязки UDP сокета к {LISTEN_HOST}:{PORT}: {e}")
            sys.exit(1)

        print(f"UDP Time Client запущен. Ожидание сообщений на порту {PORT}...")
        print("Нажмите Ctrl+C для остановки.")

        try:
            while True:
                try:
                    data, addr = s.recvfrom(BUFFER_SIZE)
                    message = data.decode('utf-8')
                    print(f"Получено от {addr}: {message}") 
                except socket.timeout:
                    continue
                except socket.error as e:
                    print(f"Ошибка при получении UDP пакета: {e}")
                    continue

        except KeyboardInterrupt:
            print("\nUDP Time Client останавливается...")
        except Exception as e:
            print(f"\nПроизошла ошибка в клиенте: {e}")
        finally:
            print("UDP Time Client остановлен.")

if __name__ == "__main__":
    run_udp_time_client()