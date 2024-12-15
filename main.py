import socket
import threading
import Server

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 8443))
    server_socket.listen(5)
    print("HTTP/2 server listening on port 8443")
    
    while True:
        client_socket, addr = server_socket.accept()
        client_ip, client_port = addr
        print(f"Connection from {client_ip}:{client_port}")
        # print(f"Connection from {addr}")
        Server.handle_client(client_socket)
        client_handler = threading.Thread(target=Server.handle_client, args=(client_socket,))
        client_handler.start()

if __name__ == "__main__":
    main()