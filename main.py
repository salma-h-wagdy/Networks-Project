import socket
import threading
import Server
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 8443))
    server.listen(5)
    print("Server listening on port 8443")

    while True:
        client_socket, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=Server.handle_client, args=(client_socket,))
        client_handler.start()

if __name__ == "__main__":
    main()