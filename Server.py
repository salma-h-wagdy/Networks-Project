import socket
import threading
import base64


users = {'user': '0000',
         'user1': '0000',
         'user2': '0000',
         'salma': '0000',
         'fatma': '0000',
         'menna': '0000'}

connected_clients = []

def authenticate(client_socket):
    encoded_credentials = client_socket.recv(1024).decode('utf-8').strip()
    decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
    username, password = decoded_credentials.split(':')

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
            #receive data from the client
            request = client_socket.recv(1024).decode('utf-8')
            if not request:
                break
            print(f"Received: {request}")

            #send a response back 
            response = f"Echo: {request} \n"
            client_socket.send(response.encode('utf-8'))
    except ConnectionResetError:
        print("Client disconnected")
    finally:
        connected_clients.remove(client_socket)
        client_socket.close()