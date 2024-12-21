import Authentication
import os

connected_clients = []

def server_status():
    """Monitor the server's status and print connected clients."""
    while True:
        command = input("Enter 'status' to see the server status: ")
        if command == 'status':
            print(f"Number of connected clients: {len(connected_clients)}")

def handle_get(path):
    """Handle GET requests."""
    file_name = path.lstrip("/")
    if path == "/status":
        return f"HTTP/1.1 200 OK\n\nConnected clients: {len(connected_clients)}"
    elif os.path.exists(file_name) and file_name.endswith(".html"):
        try:
            with open(file_name, "r") as file:
                content = file.read()
            return f"HTTP/1.1 200 OK\nContent-Type: text/html\n\n{content}"
        except Exception as e:
            return f"HTTP/1.1 500 Internal Server Error\n\nError: {str(e)}"
    else:
        return "HTTP/1.1 404 Not Found\n\nPath not found"

def handle_post(path, payload):
    """Handle POST requests."""
    if path == "/submit":
        # Process payload (e.g., save data)
        return f"HTTP/1.1 200 OK\n\nReceived payload: {payload}"
    else:
        return "HTTP/1.1 404 Not Found\n\nPath not found"

def handle_client(client_socket):
    """Handle communication with a client."""
    if not Authentication.authenticate(client_socket):
        client_socket.close()
        return

    connected_clients.append(client_socket)
    try:
        while True:
            # Receive data from the client
            request = client_socket.recv(1024).decode('utf-8').strip()
            if not request:
                break

            # Parse the request
            method, path, *rest = request.split(maxsplit=2)
            if method == "GET":
                response = handle_get(path)
            elif method == "POST":
                payload = rest[-1] if rest else ""
                response = handle_post(path, payload)
            else:
                response = "HTTP/1.1 400 Bad Request\n\nUnsupported method"

            # Send the response
            client_socket.send(response.encode('utf-8'))
    except ConnectionResetError:
        print("Client disconnected")
    finally:
        connected_clients.remove(client_socket)
        client_socket.close()
