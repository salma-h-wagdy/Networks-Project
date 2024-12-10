import Authentication

connected_clients = []


def parse_http_request(request):
    headers, body = request.split('\r\n\r\n', 1)
    header_lines = headers.split('\r\n')
    method, path, _ = header_lines[0].split()
    headers_dict = {}
    for line in header_lines[1:]:
        key, value = line.split(': ', 1)
        headers_dict[key] = value
    return method, path, headers_dict, body

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
            
            method, path, headers, body = parse_http_request(request)
            
            #send a response back 
            if method == 'POST' and path == '/message':
                print(f"Received: {body}")
                # Send a response back to the client
                response = f"HTTP/1.1 200 OK\r\nContent-Length: {len(body) + 6}\r\n\r\nEcho: {body}\n"
                client_socket.send(response.encode('utf-8'))
                
    except ConnectionResetError:
        print("Client disconnected")
    finally:
        connected_clients.remove(client_socket)
        client_socket.close()