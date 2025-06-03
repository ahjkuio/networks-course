#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import time
import datetime
import sys

BROADCAST_HOST = '<broadcast>'
PORT = 12346
INTERVAL_SECONDS = 1

def run_udp_time_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        try:
            s.bind(("", PORT))
        except socket.error as e:
            print(f"Ошибка привязки UDP сокета сервера: {e}")
            print("Убедитесь, что порт не занят другим процессом.")
            sys.exit(1)

        print(f"UDP Time Server запущен. Рассылка времени на {BROADCAST_HOST}:{PORT} каждую секунду...")
        print("Нажмите Ctrl+C для остановки.")

        try:
            while True:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                message = f"Текущее время сервера: {current_time}".encode('utf-8')
                
                try:
                    s.sendto(message, (BROADCAST_HOST, PORT))
                    print(f"Отправлено: {current_time}", end='\r')
                except socket.error as e:
                    print(f"\nОшибка отправки UDP пакета: {e}")
                    time.sleep(INTERVAL_SECONDS)
                    continue 

                time.sleep(INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\nUDP Time Server останавливается...")
        except Exception as e:
            print(f"\nПроизошла ошибка в сервере: {e}")
        finally:
            print("\nUDP Time Server остановлен.")

if __name__ == "__main__":
    run_udp_time_server()