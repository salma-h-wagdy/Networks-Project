import socket

def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 9999))

    while True:
        # Receive and print the server's message
        server_message = client.recv(1024).decode('utf-8')
        print(server_message, end='')

        # Send user input to the server
        user_input = input()
        client.send(user_input.encode('utf-8'))

if __name__ == "__main__":
    start_client()
