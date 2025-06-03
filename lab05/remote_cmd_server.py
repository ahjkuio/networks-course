#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import subprocess
import sys

HOST = '127.0.0.1'  # Слушаем на локальном хосте
PORT = 12345        # Произвольный порт, не занятый другими службами
BUFFER_SIZE = 4096  # Размер буфера для приема/отправки данных

def run_server():
    # Создаем TCP/IP сокет
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Позволяет переиспользовать адрес
        try:
            s.bind((HOST, PORT))
        except socket.error as e:
            print(f"Ошибка привязки сокета: {e}")
            sys.exit(1)
            
        s.listen()
        print(f"Сервер запущен и слушает на {HOST}:{PORT}...")

        while True:
            try:
                conn, addr = s.accept()
                with conn:
                    print(f"Подключен клиент: {addr}")
                    
                    # Получаем команду от клиента
                    command_bytes = conn.recv(BUFFER_SIZE)
                    if not command_bytes:
                        print(f"Клиент {addr} отключился без отправки команды.")
                        continue
                    
                    command = command_bytes.decode('utf-8').strip()
                    print(f"Получена команда от {addr}: {command}")

                    if command.lower() == 'exit':
                        print(f"Клиент {addr} запросил завершение. Соединение закрыто.")
                        conn.sendall("Сервер: Команда 'exit' получена. Соединение закрыто.\n".encode('utf-8'))
                        continue # Готовы к новому соединению

                    # Выполняем команду
                    try:
                        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        stdout, stderr = process.communicate(timeout=15)
                        
                        exit_code = process.returncode
                        
                        response = f"Код возврата: {exit_code}\n"
                        if stdout:
                            response += f"--- STDOUT ---\n{stdout}"
                        if stderr:
                            response += f"--- STDERR ---\n{stderr}"
                        
                        if not stdout and not stderr:
                            response += "(нет вывода stdout/stderr)"

                    except subprocess.TimeoutExpired:
                        response = "Ошибка: Команда выполнялась слишком долго и была прервана."
                        print(response)
                    except Exception as e:
                        response = f"Ошибка выполнения команды на сервере: {e}"
                        print(response)
                    
                    # Отправляем результат клиенту
                    conn.sendall(response.encode('utf-8'))
                    print(f"Результат отправлен клиенту {addr}")

            except socket.timeout:
                print("Таймаут ожидания соединения...")
                continue # Возвращаемся к ожиданию нового соединения
            except KeyboardInterrupt:
                print("\nСервер останавливается...")
                break
            except Exception as e:
                print(f"Произошла ошибка на сервере: {e}")
                continue 
                
if __name__ == "__main__":
    run_server() 