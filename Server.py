# import socket
# import threading
import ssl
import os
from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived, StreamEnded, WindowUpdated, SettingsAcknowledged, StreamReset, PriorityUpdated
from h2.exceptions import ProtocolError , StreamClosedError
# from h2.errors import ErrorCodes
import logging

import Authentication

logging.basicConfig(level=logging.DEBUG)
connected_clients = []

def server_status():
    while True:
        command = input("Enter 'status' to see the server status: ")
        if command == 'status':
            print(f"Number of connected clients: {len(connected_clients)}")
    
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
    stream_windows = {}
    stream_states = {}
    connection_window = 65535  # Initial connection flow control window size

    try:
        # authenticated = False
        while True:
            data = secure_socket.recv(65535)
            if not data:
                break

            events = conn.receive_data(data)
            for event in events:
                logging.debug(f"Event received: {event}")
                if isinstance(event, RequestReceived):
                    headers = event.headers
                    headers_dict = {k.decode('utf-8'): v.decode('utf-8') for k, v in headers}
                    path = headers_dict.get(':path', '/')
                    # logging.debug(f'Path accessed: {path}')
                    stream_windows[event.stream_id] = 65535  # Initial stream flow control window size
                    stream_states[event.stream_id] = 'open'
                    if path == '/':
                        # HTML file
                        with open('templates/auth.html', 'r') as f:
                            html_content = f.read()

                        response_headers = [
                            (':status', '200'),
                            ('content-length', str(len(html_content))),
                            ('content-type', 'text/html'),
                        ]
                        conn.send_headers(event.stream_id, response_headers)
                        conn.send_data(event.stream_id, html_content.encode('utf-8'), end_stream=True)
                        
                        if conn.remote_settings.enable_push:
                            try:
                                push_stream_id = conn.get_next_available_stream_id()
                                push_headers = [
                                    (':method', 'GET'),
                                    (':authority', 'localhost:8443'),
                                    (':scheme', 'https'),
                                    (':path', '/style.css')
                                ]
                                conn.push_stream(event.stream_id, push_stream_id, push_headers)
                                with open('style.css', 'r') as f:
                                    css_content = f.read()
                                push_response_headers = [
                                    (':status', '200'),
                                    ('content-length', str(len(css_content))),
                                    ('content-type', 'text/css'),
                                ]
                                conn.send_headers(push_stream_id, push_response_headers)
                                conn.send_data(push_stream_id, css_content.encode('utf-8'), end_stream=True)
                            except ProtocolError:
                                logging.info("Server push is disabled by the client.")
                        
                    elif path == '/authenticate':
                        auth_header = headers_dict.get('authorization', None)
                        if auth_header and ':' not in auth_header:
                            # it's a nonce request
                            nonce = Authentication.generate_nonce()
                            response_headers = [
                                (':status', '401'),
                                ('www-authenticate', f'Digest realm="test", nonce="{nonce}"')
                            ]
                            conn.send_headers(event.stream_id, response_headers, end_stream=True)
                        else:
                            # authentication request
                            authenticated = Authentication.authenticate(headers_dict, nonce)
                            # logging.debug(f'Authentication result: {authenticated}')
                            if not authenticated:
                                response_headers = [
                                    (':status', '401'),
                                    ('www-authenticate', f'Digest realm="test", nonce="{nonce}"')
                                ]
                                conn.send_headers(event.stream_id, response_headers, end_stream=True)
                            else:
                                # authenticated = True
                                # successful response after authentication
                                response_headers = [
                                    (':status', '200'),
                                    ('content-length', '13'),
                                    ('content-type', 'text/plain'),
                                ]
                                conn.send_headers(event.stream_id, response_headers)
                                conn.send_data(event.stream_id, b'Success! :D', end_stream=True)
                        

                elif isinstance(event, DataReceived):
                    conn.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
                
                elif isinstance(event, StreamEnded):
                    stream_states[event.stream_id] = 'half-closed (remote)'
                    try:
                        conn.end_stream(event.stream_id)
                    except StreamClosedError:
                        logging.info(f"Stream {event.stream_id} already closed.")
                    
                elif isinstance(event, WindowUpdated):
                    logging.debug(f"Window updated: stream_id={event.stream_id}, increment={event.delta}")
                    if event.stream_id == 0:
                        # Connection-level window update
                        connection_window += event.delta
                    else:
                        # Stream-level window update
                        if event.stream_id in stream_windows:
                            stream_windows[event.stream_id] += event.delta
                        else:
                            logging.warning(f"Stream {event.stream_id} not found in stream_windows dictionary.")
                elif isinstance(event, SettingsAcknowledged):
                    # Handle settings acknowledgment
                    pass
                elif isinstance(event, StreamReset):
                    stream_states[event.stream_id] = 'closed'
                    logging.info(f'Stream {event.stream_id} reset')
                elif isinstance(event, PriorityUpdated):
                    logging.info(f'Stream {event.stream_id} priority updated: {event.weight}, {event.depends_on}, {event.exclusive}')

                    
            secure_socket.sendall(conn.data_to_send())

    # except ConnectionResetError:
    #     print("Client disconnected")
    finally:
        connected_clients.remove(secure_socket)
        secure_socket.close()

    
