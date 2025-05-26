import socket
import sys

BUFFER_SIZE = 4096

def main():
    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} <server_host> <server_port> <filename>")
        sys.exit(1)

    server_host = sys.argv[1]
    
    try:
        server_port = int(sys.argv[2])
        if not (0 <= server_port <= 65535):
            raise ValueError("Port number must be between 0 and 65535")
    except ValueError as e:
        print(f"Error: Invalid port number '{sys.argv[2]}'. {e}")
        sys.exit(1)
        
    filename = sys.argv[3]
    if not filename.startswith('/'):
        request_path = "/" + filename
    else:
        request_path = filename

    client_socket = None 
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Connecting to {server_host}:{server_port}...")
        
        client_socket.connect((server_host, server_port))
        print("Connected to server.")

        request_lines = [
            f"GET {request_path} HTTP/1.1",
            f"Host: {server_host}:{server_port}",
            "Connection: close",
            "Accept: */*"
        ]
        http_request = "\r\n".join(request_lines) + "\r\n\r\n"

        print("--- Sending Request ---")
        print(http_request.rstrip('\r\n')) 
        print("-----------------------")
        
        client_socket.sendall(http_request.encode('utf-8'))

        print("\n--- Server Response ---")
        full_response = b""
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break
            full_response += data
        
        try:
            print(full_response.decode('utf-8'))
        except UnicodeDecodeError:
            print("Received binary data (or non-UTF-8 encoded text).")
            print(f"Received {len(full_response)} bytes.")

        print("-----------------------")

    except socket.gaierror as e:
        print(f"Error: Could not resolve host '{server_host}'. {e}")
    except socket.error as e:
        print(f"Socket error: {e}")
    except ConnectionRefusedError:
        print(f"Error: Connection to {server_host}:{server_port} refused. Is the server running?")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if client_socket:
            print("Closing socket.")
            client_socket.close()

if __name__ == '__main__':
    main() 