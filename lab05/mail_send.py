#!/usr/bin/env python3
"""Минимальный почтовый клиент (форматы txt и html).

Пример запуска:
    SMTP_HOST=smtp.example.com SMTP_PORT=587 SMTP_USER=me@example.com \
    python3 mail_send.py recipient@example.com --html index.html

Переменные окружения:
    SMTP_HOST  адрес smtp-сервера
    SMTP_PORT  порт (обычно 587 или 465 для SSL)
    SMTP_USER  учётка

Если указан --html файл, письмо будет html, иначе plain-text.
"""
from __future__ import annotations
import os
import sys
import argparse
import smtplib
import getpass
from email.message import EmailMessage


def build_message(sender: str, recipient: str, subject: str, text: str, html: str | None = None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    if html:
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(text)
    return msg


def send_email(msg: EmailMessage):
    host = os.getenv("SMTP_HOST")
    port_str = os.getenv("SMTP_PORT", "587") # По умолчанию 587 для STARTTLS
    user = os.getenv("SMTP_USER")
    
    if not all([host, user]):
        print("SMTP_HOST and SMTP_USER env vars not set", file=sys.stderr)
        sys.exit(1)

    try:
        port = int(port_str)
    except ValueError:
        print(f"Invalid SMTP_PORT: {port_str}. Must be an integer.", file=sys.stderr)
        sys.exit(1)

    pwd = getpass.getpass(f"Enter password for {user} on {host}:{port}: ")

    try:
        if port == 465: # Используем SMTP_SSL для порта 465
            with smtplib.SMTP_SSL(host, port) as smtp:
                smtp.login(user, pwd)
                smtp.send_message(msg)
        else: # Для других портов (например, 587) используем STARTTLS
            with smtplib.SMTP(host, port) as smtp:
                smtp.starttls()
                smtp.login(user, pwd)
                smtp.send_message(msg)
        print("Email sent successfully")
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e}", file=sys.stderr)
        print("Please check your username/password and SMTP settings.", file=sys.stderr)
        print("If using a service like GMail/VK Mail, you might need an 'app password'.", file=sys.stderr)
        sys.exit(1)
    except smtplib.SMTPException as e:
        print(f"SMTP Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Send email (txt or html)")
    parser.add_argument("recipient", help="email получателя")
    parser.add_argument("--subject", default="Hello from Python", help="тема письма")
    parser.add_argument("--text", default="Привет! Это текстовое письмо.")
    parser.add_argument("--html", help="путь к html-файлу для html письма")
    args = parser.parse_args()

    sender = os.getenv("SMTP_USER")
    if not sender:
        print("SMTP_USER environment variable not set.", file=sys.stderr)
        sys.exit("Error: SMTP_USER environment variable is required.")

    html_content = None
    if args.html:
        with open(args.html, "r", encoding="utf-8") as f:
            html_content = f.read()
    msg = build_message(sender, args.recipient, args.subject, args.text, html_content)
    send_email(msg)


if __name__ == "__main__":
    main() 