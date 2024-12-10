import Authentication

connected_clients = []
    
def handle_client(client_socket):
    if not Authentication.authenticate(client_socket):
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