import socket
import threading

users = {'user': '0000',
         'user1': '0000',
         'user2': '0000',
         'salma': '0000',
         'fatma': '0000',
         'menna': '0000'}

connected_clients = []

def authenticate(client_socket):
    client_socket.send(b"Username: ")
    username = client_socket.recv(1024).decode('utf-8').strip()
    client_socket.send(b"Password: ")
    password = client_socket.recv(1024).decode('utf-8').strip()

    if username in users and users[username] == password:
        client_socket.send(b"Authentication successful\n")
        return True
    else:
        client_socket.send(b"Authentication failed\nConnection Terminated")
        return False
    
def handle_client(client_socket):
    if not authenticate(client_socket):
        client_socket.close()
        return

    connected_clients.append(client_socket)
    try:
        while True:
            # Receive data from the client
            request = client_socket.recv(1024).decode('utf-8')
            if not request:
                break
            print(f"Received: {request}")

            # Send a response back to the client
            response = f"Echo: {request} \n"
            client_socket.send(response.encode('utf-8'))
    except ConnectionResetError:
        print("Client disconnected")
    finally:
        connected_clients.remove(client_socket)
        client_socket.close()