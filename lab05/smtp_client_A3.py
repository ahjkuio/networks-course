#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import base64
import ssl
import sys
import getpass
import os
import mimetypes # Для определения Content-Type изображения
from email.utils import formatdate # Для заголовка Date

def ensure_utf8(text):
    if isinstance(text, bytes):
        return text.decode('utf-8', errors='ignore')
    return str(text)

def send_email_with_attachment(
    sender_email, 
    sender_password, 
    receiver_email, 
    subject, 
    message_body, 
    attachment_path
):
    smtp_server = 'smtp.mail.ru'
    port = 587
    print_prefix = "S:"

    # Определяем Content-Type вложения
    content_type_attachment, _ = mimetypes.guess_type(attachment_path)
    if content_type_attachment is None:
        content_type_attachment = 'application/octet-stream'
    
    boundary = "----=_NextPart_000_" + base64.urlsafe_b64encode(os.urandom(15)).decode().replace('=','')

    try:
        with open(attachment_path, 'rb') as f:
            attachment_data = f.read()
        attachment_encoded = base64.b64encode(attachment_data).decode('ascii')
        attachment_filename = os.path.basename(attachment_path)
    except FileNotFoundError:
        print(f"Error: Attachment file not found at {attachment_path}")
        return
    except Exception as e:
        print(f"Error reading or encoding attachment: {e}")
        return

    # Формируем тело письма в формате multipart/mixed
    email_parts = []
    email_parts.append(f"--{boundary}")
    email_parts.append("Content-Type: text/plain; charset=\"utf-8\"")
    email_parts.append("Content-Transfer-Encoding: 8bit")
    email_parts.append("")
    email_parts.append(ensure_utf8(message_body))
    
    email_parts.append(f"--{boundary}")
    email_parts.append(f"Content-Type: {content_type_attachment}; name=\"{attachment_filename}\"")
    email_parts.append("Content-Transfer-Encoding: base64")
    email_parts.append(f"Content-Disposition: attachment; filename=\"{attachment_filename}\"")
    email_parts.append("")
    
    for i in range(0, len(attachment_encoded), 76):
        email_parts.append(attachment_encoded[i:i+76])
        
    email_parts.append(f"--{boundary}--")
    
    full_message_body = "\r\n".join(email_parts)

    # Основные заголовки письма
    headers = (
        f"From: {ensure_utf8(sender_email)}\r\n"
        f"To: {ensure_utf8(receiver_email)}\r\n"
        f"Subject: {ensure_utf8(subject)}\r\n"
        f"Date: {formatdate(localtime=True)}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: multipart/mixed; boundary=\"{boundary}\"\r\n"
        f"\r\n" 
    )
    
    final_email_to_send = headers + full_message_body + "\r\n.\r\n"

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

        print("C: Sending email (headers and multipart body)...")
        ssl_socket.sendall(final_email_to_send.encode('utf-8'))
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
        closed_main_socket = False
        if 'ssl_socket' in locals() and ssl_socket.fileno() != -1:
            try:
                ssl_socket.shutdown(socket.SHUT_RDWR)
            except socket.error: pass 
            ssl_socket.close()
            closed_main_socket = True
            print("SSL socket closed.")
        
        if not closed_main_socket and 'client_socket' in locals() and client_socket.fileno() != -1:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except socket.error: pass
            client_socket.close()
            print("Client socket closed.")

    print(f'Email to {receiver_email} with attachment processed.')

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Использование: python3 {sys.argv[0]} <адрес_получателя> <путь_к_файлу_вложения>")
        sys.exit(1)

    SENDER_EMAIL_CONST = 'st085972@student.spbu.ru'
    receiver_email_arg = sys.argv[1]
    attachment_file_path = sys.argv[2]
    smtp_server_for_prompt = 'smtp.mail.ru'
    
    if not os.path.exists(attachment_file_path):
        print(f"Ошибка: Файл вложения не найден по пути: {attachment_file_path}")
        sys.exit(1)

    try:
        sender_password_input = getpass.getpass(f"Enter password for {SENDER_EMAIL_CONST} on {smtp_server_for_prompt}: ")
    except Exception as e:
        print(f"Не удалось получить пароль: {e}")
        sys.exit(1)
    
    if not sender_password_input:
        print("Пароль не введен. Выход.")
        sys.exit(1)

    subject_line = ensure_utf8('Тестовое письмо с вложением (сокеты, A.3)')
    body_text = ensure_utf8('Это текстовое сообщение, отправленное SMTP-клиентом Python.\nПисьмо содержит вложенный файл.')

    print(f"\nAttempting to send an email with attachment {attachment_file_path} to {receiver_email_arg}...")
    send_email_with_attachment(
        SENDER_EMAIL_CONST, 
        sender_password_input, 
        receiver_email_arg, 
        subject_line, 
        body_text, 
        attachment_file_path
    ) 