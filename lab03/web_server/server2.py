import socket
import sys
import os
import threading

HOST = '127.0.0.1'
DEFAULT_PORT = 6789
MAX_CONN = 5
BUFFER_SIZE = 1024
WEB_ROOT = "htdocs"

def get_content_type(filepath):
    """Определяет Content-Type на основе расширения файла."""
    if filepath.endswith(".html") or filepath.endswith(".htm"):
        return "text/html; charset=utf-8"
    elif filepath.endswith(".txt"):
        return "text/plain; charset=utf-8"
    elif filepath.endswith(".jpg") or filepath.endswith(".jpeg"):
        return "image/jpeg"
    elif filepath.endswith(".png"):
        return "image/png"
    elif filepath.endswith(".css"):
        return "text/css; charset=utf-8"
    return "application/octet-stream"

def handle_request(request_str):
    """Обрабатывает HTTP-запрос и возвращает кортеж (статус, заголовки, тело_ответа)."""
    try:
        first_line = request_str.split('\r\n')[0]
        parts = first_line.split(' ')
        if len(parts) < 2:
            return "400 Bad Request", {"Content-Type": "text/html; charset=utf-8", "Connection": "close"}, b"<html><body><h1>400 Bad Request</h1></body></html>"
        
        method = parts[0]
        requested_path = parts[1]

        if method != "GET":
            return "501 Not Implemented", {"Content-Type": "text/html; charset=utf-8", "Connection": "close"}, b"<html><body><h1>501 Not Implemented</h1></body></html>"

        if requested_path == "/":
            requested_path = "/index.html"
        
        relative_filepath = requested_path.lstrip('/') 
        filepath = os.path.join(WEB_ROOT, relative_filepath)

        if not os.path.abspath(filepath).startswith(os.path.abspath(WEB_ROOT)):
            print(f"Attempt to access file outside WEB_ROOT: {filepath}")
            return "403 Forbidden", {"Content-Type": "text/html; charset=utf-8", "Connection": "close"}, b"<html><body><h1>403 Forbidden</h1></body></html>"

        if os.path.exists(filepath) and os.path.isfile(filepath):
            try:
                with open(filepath, 'rb') as f:
                    file_content = f.read()
                
                content_type = get_content_type(filepath)
                headers = {
                    "Content-Type": content_type,
                    "Content-Length": str(len(file_content)),
                    "Connection": "close"
                }
                return "200 OK", headers, file_content
            except IOError as e:
                print(f"Error reading file {filepath}: {e}")
                return "500 Internal Server Error", {"Content-Type": "text/html; charset=utf-8", "Connection": "close"}, b"<html><body><h1>500 Internal Server Error</h1><p>Could not read file.</p></body></html>"
        else:
            print(f"File not found: {filepath}")
            error_body = f"<html><body><h1>404 Not Found</h1><p>File requested: {requested_path}</p></body></html>".encode('utf-8')
            headers = {
                "Content-Type": "text/html; charset=utf-8",
                "Content-Length": str(len(error_body)),
                "Connection": "close"
            }
            return "404 Not Found", headers, error_body

    except Exception as e:
        print(f"Error processing request: {e}")
        return "500 Internal Server Error", {"Content-Type": "text/html; charset=utf-8", "Connection": "close"}, b"<html><body><h1>500 Internal Server Error</h1><p>An error occurred while processing the request.</p></body></html>"

def handle_client_connection(client_socket, client_address):
    """Обрабатывает соединение с одним клиентом."""
    try:
        print(f"Thread started for {client_address}")
        request_data = client_socket.recv(BUFFER_SIZE)
        if not request_data:
            print(f"Client {client_address} sent empty data or closed connection prematurely.")
            client_socket.close()
            return
        
        request_str = request_data.decode('utf-8')
        print(f"--- Received Request from {client_address} ---")
        print(request_str)
        print("------------------------")

        status, headers, body = handle_request(request_str)
        
        response_lines = [f"HTTP/1.1 {status}"]
        for key, value in headers.items():
            response_lines.append(f"{key}: {value}")
        response_lines.append("\r\n")
        
        http_response_header = "\r\n".join(response_lines).encode('utf-8')
        http_response = http_response_header + body

        client_socket.sendall(http_response)
        print(f"Sent HTTP response to {client_address}.")

    except socket.error as err:
        print(f"Error during communication with {client_address}: {err}")
    except UnicodeDecodeError:
        print(f"Error decoding request from {client_address}. Not UTF-8?")
    finally:
        print(f"Closing connection with {client_address}.")
        client_socket.close()
        print(f"Thread for {client_address} finished.")

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <port>")
        print(f"Using default port {DEFAULT_PORT}")
        port = DEFAULT_PORT
    else:
        try:
            port = int(sys.argv[1])
            if not (1024 <= port <= 65535):
                raise ValueError("Port number must be between 1024 and 65535")
        except ValueError as e:
            print(f"Error: Invalid port number '{sys.argv[1]}'. {e}")
            sys.exit(1)

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Socket created successfully")
    except socket.error as err:
        print(f"Socket creation failed with error {err}")
        sys.exit(1)

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, port))
        print(f"Socket bound to port {port}")
    except socket.error as err:
        print(f"Socket binding failed with error {err}")
        server_socket.close()
        sys.exit(1)

    try:
        server_socket.listen(MAX_CONN)
        print(f"Server is listening on {HOST}:{port}...")
    except socket.error as err:
        print(f"Server listen failed with error {err}")
        server_socket.close()
        sys.exit(1)

    try:
        while True:
            print('\nWaiting for a new connection...')
            try:
                client_socket, client_address = server_socket.accept()
                print(f"Accepted connection from: {client_address}")
                
                client_thread = threading.Thread(target=handle_client_connection, args=(client_socket, client_address))
                client_thread.start()
                
            except socket.error as err:
                print(f"Accepting connection failed with error {err}")
                continue

    except KeyboardInterrupt:
        print("\nServer is shutting down.")
    finally:
        print("Closing server socket.")
        server_socket.close()

if __name__ == '__main__':
    main() 