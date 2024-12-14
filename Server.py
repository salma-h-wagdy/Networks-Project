import socket
import ssl
import threading
import base64
import hashlib
import time
import os
from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived, StreamEnded
import logging


import Authentication
logging.basicConfig(level=logging.DEBUG)
connected_clients = []
    
def handle_client(client_socket):
    # if not Authentication.authenticate(client_socket):
    #     client_socket.close()
    #     return
    
    if not os.path.exists("server.crt") or not os.path.exists("server.key"):
        raise FileNotFoundError("SSL certificate or key file not found.")
    
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile='server.crt', keyfile='server.key') 
    context.set_alpn_protocols(['h2'])
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
     
    secure_socket = context.wrap_socket(client_socket, server_side=True)  
    
    conn = H2Connection(H2Configuration(client_side=False))
    conn.initiate_connection()
    secure_socket.sendall(conn.data_to_send())
    
    # nonce = Authentication.generate_nonce()

    connected_clients.append(secure_socket)
    try:
        # authenticated = False
        while True:
            data = secure_socket.recv(65535)
            if not data:
                break

            events = conn.receive_data(data)
            for event in events:
                if isinstance(event, RequestReceived):
                    headers = event.headers
                    #print recieved headers
                    print(f"headres: {headers}")
                    headers_dict = {k.decode('utf-8'): v.decode('utf-8') for k, v in headers}
                    path = headers_dict.get(':path', '/')
                    print(f"path accessed {path}")
                    if path == '/':
                        # Serve the HTML file
                        with open('auth.html', 'r') as f:
                            html_content = f.read()

                        response_headers = [
                            (':status', '200'),
                            ('content-length', str(len(html_content))),
                            ('content-type', 'text/html'),
                        ]
                        conn.send_headers(event.stream_id, response_headers)
                        conn.send_data(event.stream_id, html_content.encode('utf-8'), end_stream=True)
                    elif path == '/authenticate':
                        auth_header = headers_dict.get('authorization', None)
                        if auth_header and ':' not in auth_header:
                            # This is a nonce request
                            nonce = Authentication.generate_nonce()
                            response_headers = [
                                (':status', '401'),
                                ('www-authenticate', f'Digest realm="test", nonce="{nonce}"')
                            ]
                            conn.send_headers(event.stream_id, response_headers, end_stream=True)
                        else:
                            # This is an authentication request
                            authenticated = Authentication.authenticate(headers_dict, nonce)
                            logging.debug(f'Authentication result: {authenticated}')
                            if not authenticated:
                                response_headers = [
                                    (':status', '401'),
                                    ('www-authenticate', f'Digest realm="test", nonce="{nonce}"')
                                ]
                                conn.send_headers(event.stream_id, response_headers, end_stream=True)
                            else:
                                # authenticated = True
                                # Send successful response after authentication
                                response_headers = [
                                    (':status', '200'),
                                    ('content-length', '13'),
                                    ('content-type', 'text/plain'),
                                ]
                                conn.send_headers(event.stream_id, response_headers)
                                conn.send_data(event.stream_id, b'Success! :D', end_stream=True)
                        
                    # else:   
                    #     response_headers = [
                    #         (':status', '200'),
                    #         ('content-length', '13'),
                    #         ('content-type', 'text/plain'),
                    #     ]
                        # conn.send_headers(event.stream_id, response_headers)
                        # conn.send_data(event.stream_id, b'Hello, world!', end_stream=True)

                elif isinstance(event, DataReceived):
                    # Process incoming data here
                    pass
                
                elif isinstance(event, StreamEnded):
                    # Stream ended
                    pass

            secure_socket.sendall(conn.data_to_send())

    except ConnectionResetError:
        print("Client disconnected")
    finally:
        connected_clients.remove(secure_socket)
        secure_socket.close()

    
    
    
    
    
    
    
    # connected_clients.append(client_socket)
    # try:
    #     while True:
    #         #receive data from the client
    #         request = client_socket.recv(1024).decode('utf-8')
    #         if not request:
    #             break
    #         print(f"Received: {request}")

    #         #send a response back 
    #         response = f"Echo: {request} \n"
    #         client_socket.send(response.encode('utf-8'))
    # except ConnectionResetError:
    #     print("Client disconnected")
    # finally:
    #     connected_clients.remove(client_socket)
    #     client_socket.close()