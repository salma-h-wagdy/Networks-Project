import base64
import hashlib
import time
import os
import Server


users = {'user': '0000',
         'user1': '0000',
         'user2': '0000',
         'salma': '0000',
         'fatma': '0000',
         'menna': '0000'}

def generate_nonce():
    timestamp = str(time.time()).encode('utf-8')
    random_bytes = os.urandom(16)
    nonce = base64.b64encode(timestamp + random_bytes).decode('utf-8')
    return nonce

def sha256_hash(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def authenticate(client_socket):
    nonce = generate_nonce()
    client_socket.send(f"Nonce: {nonce}\n".encode('utf-8'))
    
    request = client_socket.recv(1024).decode('utf-8').strip()
    method, path, headers, body = Server.parse_http_request(request)
   
    if method == 'POST' and path == '/authenticate':
        encoded_credentials , client_hash = body.split(':')
        
        username, password = base64.b64decode(encoded_credentials).decode('utf-8').split(':')
        
        server_hash = sha256_hash(f"{username}:{password}:{nonce}")
        
        if username in users and users[username] == password and client_hash == server_hash:
            client_socket.send(b"HTTP/1.1 200 OK\r\nContent-Length: 24\r\n\r\nAuthentication successful\n")
            return True
        else:
            client_socket.send(b"HTTP/1.1 401 Unauthorized\r\nContent-Length: 18\r\n\r\nAuthentication failed\n")
            return False