import base64
import hashlib
import time
import os
import socket
import ssl
import threading
from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived, StreamEnded
import logging

logging.basicConfig(level=logging.DEBUG)


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

def authenticate(headers, nonce): #client_socket
    # headers_dict = {}
    auth_header = headers.get('authorization', None)
    auth_header = dict(headers).get('authorization', None)
    print(f"authorization : {auth_header}")
    # auth_header = headers.get('authorization', None)
    if not auth_header:
        return False
    
    try:
        encoded_credentials, client_hash = auth_header.split(':')
        username, password = base64.b64decode(encoded_credentials).decode('utf-8').split(':')
        server_hash = sha256_hash(f"{username}:{password}:{nonce}")
        print(f"client hash{client_hash}, server: {server_hash}")
        
        if username in users and users[username] == password and client_hash == server_hash:
            return True
    except Exception as e:
        logging.error(f'Error during authentication: {e}')
    return False
    
    # nonce = generate_nonce()
    # client_socket.send(f"Nonce: {nonce}\n".encode('utf-8'))
    
    # encoded_response = client_socket.recv(1024).decode('utf-8').strip()
    # encoded_credentials , client_hash = encoded_response.split(':')
    
    # username, password = base64.b64decode(encoded_credentials).decode('utf-8').split(':')
    
    # server_hash = sha256_hash(f"{username}:{password}:{nonce}")
    
    # if username in users and users[username] == password and client_hash == server_hash:
    #     client_socket.send(b"Authentication successful\n")
    #     return True
    # else:
    #     client_socket.send(b"Authentication failed\nConnection Terminated")
    #     return False