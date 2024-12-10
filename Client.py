import socket
import base64
import Authentication

def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 9999))

    username = input("Username: ")
    password = input("Password: ")
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    #authenticate using digest authentication
    server_message = client.recv(1024).decode('utf-8')
    if server_message.startswith("Nonce:"):
            nonce = server_message.split(": ")[1].strip()
            client_hash = Authentication.sha256_hash(f"{username}:{password}:{nonce}")
            auth_response = f"{encoded_credentials}:{client_hash}"
            http_request = f"POST /authenticate HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(auth_response)}\r\n\r\n{auth_response}"
            client.send(http_request.encode('utf-8'))
            
    while True:
        # receive & print the server's message
        server_message = client.recv(1024).decode('utf-8')
        print(server_message, end='')
        
        #send user input 
        user_input = input()
        http_request = f"POST /message HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(user_input)}\r\n\r\n{user_input}"
        client.send(http_request.encode('utf-8'))
            
            
if __name__ == "__main__":
    start_client()
