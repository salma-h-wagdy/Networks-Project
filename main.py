import socket
import threading
import Server

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8443))
    server_socket.listen(5)
    print("HTTP/2 server listening on port 8443")
    
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        Server.handle_client(client_socket)
        client_handler = threading.Thread(target=Server.handle_client, args=(client_socket,))
        client_handler.start()

if __name__ == "__main__":
    main()