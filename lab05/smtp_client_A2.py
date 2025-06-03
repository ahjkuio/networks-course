#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import base64
import ssl
import sys
import getpass

def ensure_utf8(text):
    if isinstance(text, bytes):
        return text.decode('utf-8', errors='ignore')
    return str(text)

def send_email_raw_socket(sender_email, sender_password, receiver_email, subject, message_body, content_type='text/plain; charset=utf-8'):
    smtp_server = 'smtp.mail.ru'
    port = 587
    print_prefix = "S:"

    try:
        print(f"Connecting to {smtp_server}:{port}...")
        client_socket = socket.create_connection((smtp_server, port), timeout=15)
        response = client_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")
        if not response.startswith('220'): raise Exception("Connection failed")

        print(f"C: EHLO myclient.example.com")
        client_socket.sendall(b'EHLO myclient.example.com\r\n')
        response = client_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")

        print(f"C: STARTTLS")
        client_socket.sendall(b'STARTTLS\r\n')
        response = client_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")
        if not response.startswith('220'): raise Exception("STARTTLS failed")

        context = ssl.create_default_context()
        ssl_socket = context.wrap_socket(client_socket, server_hostname=smtp_server)
        print("Connection secured with TLS.")

        print(f"C (TLS): EHLO myclient.example.com")
        ssl_socket.sendall(b'EHLO myclient.example.com\r\n')
        response = ssl_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")

        print(f"C: AUTH LOGIN")
        ssl_socket.sendall(b'AUTH LOGIN\r\n')
        response = ssl_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")
        if not response.startswith('334'): raise Exception("AUTH LOGIN not accepted or unexpected response")

        print(f"C: {sender_email} (base64)")
        ssl_socket.sendall(base64.b64encode(sender_email.encode()) + b'\r\n')
        response = ssl_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")
        if not response.startswith('334'): raise Exception("Username not accepted or unexpected response")
        
        print(f"C: ****PASSWORD**** (base64)")
        ssl_socket.sendall(base64.b64encode(sender_password.encode()) + b'\r\n')
        response = ssl_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")
        if not response.startswith('235'): raise Exception(f"Authentication failed: {response.strip()}")
        print("Authenticated successfully.")
        
        mail_from_cmd = f'MAIL FROM:<{sender_email}>\r\n'
        print(f"C: {mail_from_cmd.strip()}")
        ssl_socket.sendall(mail_from_cmd.encode())
        response = ssl_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")
        if not response.startswith('250'): raise Exception("MAIL FROM failed")

        rcpt_to_cmd = f'RCPT TO:<{receiver_email}>\r\n'
        print(f"C: {rcpt_to_cmd.strip()}")
        ssl_socket.sendall(rcpt_to_cmd.encode())
        response = ssl_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")
        if not response.startswith('250'): raise Exception("RCPT TO failed")

        print(f"C: DATA")
        ssl_socket.sendall(b'DATA\r\n')
        response = ssl_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")
        if not response.startswith('354'): raise Exception("DATA command failed")

        email_message = (
            f"From: {ensure_utf8(sender_email)}\r\n"
            f"To: {ensure_utf8(receiver_email)}\r\n"
            f"Subject: {ensure_utf8(subject)}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"MIME-Version: 1.0\r\n"
            f"\r\n"
            f"{ensure_utf8(message_body)}\r\n"
            f".\r\n"
        )

        print("C: Sending email body...")
        ssl_socket.sendall(email_message.encode('utf-8'))
        response = ssl_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")
        if not response.startswith('250'): raise Exception("Failed to send email (after DATA)")

        print(f"C: QUIT")
        ssl_socket.sendall(b'QUIT\r\n')
        response = ssl_socket.recv(1024).decode('utf-8', errors='ignore')
        print(f"{print_prefix} {response.strip()}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ssl_socket' in locals() and ssl_socket.fileno() != -1:
            try:
                ssl_socket.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass # Игнорируем ошибки при shutdown, если сокет уже закрыт
            ssl_socket.close()
            print("SSL socket closed.")
        elif 'client_socket' in locals() and client_socket.fileno() != -1:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            client_socket.close()
            print("Client socket closed.")

    print(f'Email to {receiver_email} processed.')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Использование: python3 {sys.argv[0]} <адрес_получателя>")
        sys.exit(1)

    SENDER_EMAIL_CONST = 'st085972@student.spbu.ru'
    receiver_email_arg = sys.argv[1]
    smtp_server_for_prompt = 'smtp.mail.ru' # Для корректного отображения в getpass
    
    try:
        sender_password_input = getpass.getpass(f"Enter password for {SENDER_EMAIL_CONST} on {smtp_server_for_prompt}: ")
    except Exception as e:
        print(f"Не удалось получить пароль: {e}")
        sys.exit(1)
    
    if not sender_password_input:
        print("Пароль не введен. Выход.")
        sys.exit(1)

    subject_txt = ensure_utf8('Тестовое письмо от SMTP-клиента (сокеты, A.2)')
    message_body_txt = ensure_utf8('Это текстовое сообщение, отправленное SMTP-клиентом Python с использованием сокетов, STARTTLS и AUTH LOGIN.')

    print(f"\nAttempting to send a plain text email to {receiver_email_arg}...")
    send_email_raw_socket(SENDER_EMAIL_CONST, sender_password_input, receiver_email_arg, subject_txt, message_body_txt) 