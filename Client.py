import socket
import base64
import Authentication
import h2.connection
import h2.events


def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 9999))


    conn = h2.connection.H2Connection()
    conn.initiate_connection()
    client.sendall(conn.data_to_send())
    while True:
        data = client.recv(65535)
        if not data:
            break

        events = conn.receive_data(data)
        for event in events:
            if isinstance(event, h2.events.ResponseReceived):
                headers = dict(event.headers)
                if ':status' in headers and headers[':status'] == '401':
                    www_authenticate = headers['www-authenticate']
                    nonce = www_authenticate.split('nonce="')[1].split('"')[0]
                    
                    username = input("Username: ")
                    password = input("Password: ")
                    credentials = f"{username}:{password}"
                    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                    client_hash = Authentication.sha256_hash(f"{username}:{password}:{nonce}")
                    auth_header = f'{encoded_credentials}:{client_hash}'
                    
                    headers = [
                        (':method', 'GET'),
                        (':path', '/'),
                        ('authorization', auth_header)
                    ]
                    conn.send_headers(event.stream_id, headers, end_stream=True)
                    client.sendall(conn.data_to_send())

            elif isinstance(event, h2.events.DataReceived):
                print(event.data.decode('utf-8'))

if __name__ == "__main__":
    start_client()
    
    
    # username = input("Username: ")
    # password = input("Password: ")
    # credentials = f"{username}:{password}"
    # encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    # #authenticate using digest authentication
    # server_message = client.recv(1024).decode('utf-8')
    # if server_message.startswith("Nonce:"):
    #         nonce = server_message.split(": ")[1].strip()
    #         client_hash = Authentication.sha256_hash(f"{username}:{password}:{nonce}")
    #         auth_response = f"{encoded_credentials}:{client_hash}"
    #         client.send(auth_response.encode('utf-8'))
            
    # while True:
    #     # receive & print the server's message
    #     server_message = client.recv(1024).decode('utf-8')
    #     print(server_message, end='')
        
    #     #send user input 
    #     user_input = input()
    #     client.send(user_input.encode('utf-8'))
            
            
if __name__ == "__main__":
    start_client()
