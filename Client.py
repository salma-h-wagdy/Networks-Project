import socket
import base64

def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 9999))

    username = input("Username: ")
    password = input("Password: ")
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

    #send encoded credentials
    client.send(encoded_credentials.encode('utf-8'))
    
    while True:
        # receive & print the server's message
        server_message = client.recv(1024).decode('utf-8')
        print(server_message, end='')

        # send user input to the server
        user_input = input()
        client.send(user_input.encode('utf-8'))

if __name__ == "__main__":
    start_client()
