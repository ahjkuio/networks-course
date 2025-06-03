#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import sys

HOST = '127.0.0.1'  # Адрес сервера (localhost)
PORT = 12345        # Тот же порт, что и на сервере
BUFFER_SIZE = 4096

def run_client():
    while True:
        try:
            command = input("Введите команду для удаленного выполнения (или 'exit' для выхода): ")
            if not command.strip():
                print("Команда не может быть пустой.")
                continue

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect((HOST, PORT))
                except socket.error as e:
                    print(f"Ошибка подключения к серверу {HOST}:{PORT}: {e}")
                    print("Убедитесь, что сервер запущен.")
                    # Даем возможность попробовать еще раз или выйти
                    choice = input("Попробовать еще раз? (y/n, по умолчанию y): ").lower()
                    if choice == 'n':
                        break
                    continue # Попробовать ввести команду и подключиться снова
                
                print(f"Подключено к серверу {HOST}:{PORT}")
                
                # Отправляем команду
                s.sendall(command.encode('utf-8'))
                print(f"Отправлена команда: {command}")

                # Получаем ответ
                # Сервер может отправить много данных, поэтому читаем в цикле, пока все не получим
                response_parts = []
                while True:
                    try:
                        part = s.recv(BUFFER_SIZE)
                        if not part:
                            break # Соединение закрыто сервером
                        response_parts.append(part)
                    except socket.timeout:
                        print("Таймаут ожидания ответа от сервера.")
                        break
                    except Exception as e:
                        print(f"Ошибка при получении данных: {e}")
                        break
                
                if response_parts:
                    response = b''.join(response_parts).decode('utf-8')
                    print("\n--- Ответ от сервера ---")
                    print(response)
                    print("--- Конец ответа ---\n")
                else:
                    print("Не получен ответ от сервера или соединение было закрыто.")

            if command.lower() == 'exit':
                print("Клиент завершает работу.")
                break
                
        except KeyboardInterrupt:
            print("\nКлиент прерван пользователем. Отправка команды 'exit' серверу...")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_exit:
                    s_exit.connect((HOST, PORT))
                    s_exit.sendall(b'exit')
                    # Можно подождать короткий ответ от сервера, но не обязательно для команды exit
                    # s_exit.recv(BUFFER_SIZE) 
            except Exception as e:
                print(f"Не удалось отправить 'exit' серверу при прерывании: {e}")
            break # Выход из основного цикла
        except EOFError: # Ctrl+D
            print("\nВвод завершен (EOF). Клиент завершает работу.")
            # Аналогично можно попытаться отправить 'exit'
            break
        except Exception as e:
            print(f"Произошла ошибка в клиенте: {e}")
            # Предложить продолжить или выйти
            choice = input("Произошла непредвиденная ошибка. Продолжить? (y/n, по умолчанию y): ").lower()
            if choice == 'n':
                break
            continue

if __name__ == "__main__":
    run_client() 