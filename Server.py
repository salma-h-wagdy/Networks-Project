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
            
def send_data_with_flow_control(conn, stream_id, data , connection_window , stream_windows):

    while data:
        # Determine the maximum amount of data that can be sent
        max_data = min(connection_window, stream_windows.get(stream_id, 0), len(data))
        if max_data == 0:
            # No window space available, wait for a WINDOW_UPDATE frame
            break

        # Send the data
        conn.send_data(stream_id, data[:max_data])
        data = data[max_data:]

        # Update the flow control windows
        connection_window -= max_data
        stream_windows[stream_id] -= max_data

    return connection_window, stream_windows
    
def handle_client(client_socket):
    
    if not os.path.exists("server.crt") or not os.path.exists("server.key"):
        raise FileNotFoundError("SSL certificate or key file not found.")
    
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile='server.crt', keyfile='server.key') 
    context.set_alpn_protocols(['h2'])
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
     
    try:
        secure_socket = context.wrap_socket(client_socket, server_side=True)
    except ssl.SSLError as e:
        logging.error(f"SSL error: {e}")
        client_socket.close()
        return
    except OSError as e:
        logging.error(f"Socket error: {e}")
        client_socket.close()
        return  
    
    conn = H2Connection(H2Configuration(client_side=False))
    conn.initiate_connection()
    secure_socket.sendall(conn.data_to_send())

    connected_clients.append(secure_socket)
    stream_windows = {}  # manage flow control window sizes of each stream
    stream_states = {} # track state of each stream 
    stream_priorities = {} # manage priority info of each stream
    connection_window = 65535  # Initial connection flow control window size

    try:
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
                    stream_states[event.stream_id] = 'open' # set initial state of the stream to 'open'
                     # auth html file (main page)
                    if path == '/':
                        with open('templates/auth.html', 'r') as f:
                            html_content = f.read()

                        response_headers = [
                            (':status', '200'),
                            ('content-length', str(len(html_content))),
                            ('content-type', 'text/html'),
                        ]
                        conn.send_headers(event.stream_id, response_headers)
                        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, html_content.encode('utf-8'), connection_window, stream_windows)
                        
                        #server push
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
                                connection_window, stream_windows = send_data_with_flow_control(conn, push_stream_id, css_content.encode('utf-8'), connection_window, stream_windows)
                            except ProtocolError:
                                logging.info("Server push is disabled by the client.")
                                
                    elif path == '/high-priority':
                        # Handle high-priority request
                        response_headers = [
                            (':status', '200'),
                            ('content-length', '13'),
                            ('content-type', 'text/plain'),
                        ]
                        conn.send_headers(event.stream_id, response_headers)
                        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'High Priority', connection_window, stream_windows)
                    elif path == '/low-priority':
                        # Handle low-priority request
                        response_headers = [
                            (':status', '200'),
                            ('content-length', '12'),
                            ('content-type', 'text/plain'),
                        ]
                        conn.send_headers(event.stream_id, response_headers)
                        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Low Priority', connection_window, stream_windows)
                    
                    #authentication
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
                                # successful response after authentication
                                response_headers = [
                                    (':status', '200'),
                                    ('content-length', '13'),
                                    ('content-type', 'text/plain'),
                                ]
                                conn.send_headers(event.stream_id, response_headers)
                                connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Success! :D', connection_window, stream_windows)
                        
                # Flow Control 
                elif isinstance(event, DataReceived):
                    conn.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
                
                # Stream States
                elif isinstance(event, StreamEnded):
                    stream_states[event.stream_id] = 'half-closed (remote)'
                    try:
                        conn.end_stream(event.stream_id)
                    except StreamClosedError:
                        logging.info(f"Stream {event.stream_id} already closed.")
                    
                # Flow Control
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
                
                # SETTINGS frame
                elif isinstance(event, SettingsAcknowledged):
                    logging.info("Settings acknowledged by the client.")
                    
                # RST_STREAM Frame
                elif isinstance(event, StreamReset):
                    stream_states[event.stream_id] = 'closed'
                    logging.info(f'Stream {event.stream_id} reset')
                    #additional error handling logic
                    
                #PRIORITY frame
                elif isinstance(event, PriorityUpdated):
                    logging.info(f"Stream {event.stream_id} priority updated: weight={event.weight}, depends_on={event.depends_on}, exclusive={event.exclusive}")
                    stream_priorities[event.stream_id] = {
                        'weight': event.weight,
                        'depends_on': event.depends_on,
                        'exclusive': event.exclusive
                    }
                    
            secure_socket.sendall(conn.data_to_send())
    except Exception as e:
        logging.error(f"Exception in handle_client: {e}")
    finally:
        connected_clients.remove(client_socket)
        try:
            secure_socket.close()
        except Exception as e:
            logging.error(f"Exception while closing secure_socket: {e}")
        try:
            client_socket.close()
        except Exception as e:
            logging.error(f"Exception while closing client_socket: {e}")

    # except ConnectionResetError:
    #     print("Client disconnected")
    # finally:
    #     connected_clients.remove(secure_socket)
    #     secure_socket.close()

    
