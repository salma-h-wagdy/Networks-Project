import socket
import base64
import Authentication


def send_get(client, path):
    """Send a GET request to the server."""
    request = f"GET {path} HTTP/1.1\n"
    client.send(request.encode('utf-8'))
    response = client.recv(1024).decode('utf-8')
    print(response)


def send_post(client, path, payload):
    """Send a POST request with payload to the server."""
    request = f"POST {path} HTTP/1.1\n{payload}\n"
    client.send(request.encode('utf-8'))
    response = client.recv(1024).decode('utf-8')
    print(response)


def start_client():
    """Start the client and handle user commands."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 8443))

    # Authentication
    username = input("Username: ")
    password = input("Password: ")
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

    # Authenticate with nonce
    server_message = client.recv(1024).decode('utf-8')
    if server_message.startswith("Nonce:"):
        nonce = server_message.split(": ")[1].strip()
        client_hash = Authentication.sha256_hash(f"{username}:{password}:{nonce}")
        auth_response = f"{encoded_credentials}:{client_hash}"
        client.send(auth_response.encode('utf-8'))

    # Check authentication result
    auth_result = client.recv(1024).decode('utf-8')
    print(auth_result)
    if "Authentication successful" not in auth_result:
        client.close()
        return

    # Main loop for user input
    while True:
        command = input("Enter command (GET/POST/exit): ")
        if command.lower() == "exit":
            print("Disconnecting...")
            client.close()
            break
        elif command.startswith("GET"):
            _, path = command.split(maxsplit=1)
            send_get(client, path)
        elif command.startswith("POST"):
            _, path, payload = command.split(maxsplit=2)
            send_post(client, path, payload)
        else:
            print("Invalid command. Use GET, POST, or exit.")


if __name__ == "__main__":
    start_client()
