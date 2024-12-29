# import socket
import threading
import random
import ssl
import os
import time
from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived, StreamEnded, WindowUpdated, SettingsAcknowledged, StreamReset, PriorityUpdated , RemoteSettingsChanged 
from h2.exceptions import ProtocolError , StreamClosedError
import h2.settings
# from h2.errors import ErrorCodes , refused_stream_error , REFUSED_STREAM
import h2.errors
import logging
import Cache
import Authentication
import hpack


logging.basicConfig(level=logging.DEBUG)
connected_clients = []


def encode_headers(headers):
    encoder = hpack.Encoder()
    encoded_headers = encoder.encode(headers)
    original_size = sum(len(k) + len(v) for k, v in headers)
    encoded_size = len(encoded_headers)
    logging.info("YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY")
    logging.info(f"Original header:{headers} -> {encoded_headers}")
    logging.info(f"Original headers size: {original_size} bytes")
    logging.info(f"Encoded headers size: {encoded_size} bytes")
    return encoded_headers

def decode_headers(encoded_headers):
    decoder = hpack.Decoder()
    decoded_headers = decoder.decode(encoded_headers)
    # logging.debug(f"Decoded headers: {encoded_headers} -> {decoded_headers}")
    # decoded_size = sum(len(k) + len(v) for k, v in decoded_headers)
    # logging.info(f"Encoded headers size: {len(encoded_headers)} bytes")
    # logging.info(f"Decoded headers size: {decoded_size} bytes")
    return decoded_headers


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

# Handle flow control errors
def handle_flow_control_error(conn, stream_id, error_code):
    conn.reset_stream(stream_id, error_code)
    logging.error(f"Flow control error on stream {stream_id}: {error_code}")
    
    
def send_window_update(conn, stream_id, increment):
    conn.increment_flow_control_window(increment, stream_id)
    logging.info(f"Sent WINDOW_UPDATE frame: stream_id={stream_id}, increment={increment}")

def send_goaway_frame(conn, last_stream_id, error_code=0):
    conn.close_connection(error_code=error_code, last_stream_id=last_stream_id)
    logging.info(f"Sent GOAWAY frame, closing streams after {last_stream_id} with error code {error_code}")
    
# Send PING frame
def send_ping_frame(conn):
    ping_data = random.randbytes(8)  # 8-byte random data for PING
    conn.ping(ping_data)
    logging.info("Sent PING frame")

# Periodically send PING frames to keep connection alive
def ping_thread(conn):
    while True:
        time.sleep(30)  # Send a PING every 30 seconds
        send_ping_frame(conn)
        
        
# Handle CONTINUATION frames for large headers
def send_continuation_frame(conn, stream_id, headers, offset, max_frame_size=16384):
    while offset < len(headers):
        remaining = len(headers) - offset
        chunk = headers[offset:offset + max_frame_size]
        conn.send_continuation(stream_id, chunk, end_stream=False if remaining > max_frame_size else True)
        offset += max_frame_size
    logging.info(f"Sent CONTINUATION frame for stream {stream_id}, header size: {len(headers)}")
 
   
# def send_priority_frame(conn, stream_id, weight, depends_on, exclusive):
#     conn.prioritize(stream_id, weight=weight, depends_on=depends_on, exclusive=exclusive)
#     logging.info(f"Sent PRIORITY frame: stream_id={stream_id}, weight={weight}, depends_on={depends_on}, exclusive={exclusive}")
    
def send_rst_stream_frame(conn, stream_id, error_code):
    conn.reset_stream(stream_id, error_code)
    logging.info(f"Sent RST_STREAM frame: stream_id={stream_id}, error_code={error_code}")
    
def send_settings_frame(conn, settings):
    conn.update_settings(settings)
    logging.info(f"Sent SETTINGS frame: {settings}")
    
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
    
    config = H2Configuration(client_side=False, header_encoding='utf-8')
    conn = H2Connection(config)
    conn.initiate_connection()
    secure_socket.sendall(conn.data_to_send())
    
    settings = {
        h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS: 100,
        h2.settings.SettingCodes.INITIAL_WINDOW_SIZE: 65535,
    }
    send_settings_frame(conn, settings)

    connected_clients.append(secure_socket)
    stream_windows = {}  # manage flow control window sizes of each stream
    stream_states = {} # track state of each stream 
    stream_priorities = {} # manage priority info of each stream
    connection_window = 65535  # Initial connection flow control window size
    last_stream_id = 0
    partial_headers = {}
    
    
    # Start the ping thread
    ping_thread_instance = threading.Thread(target=ping_thread, args=(conn,))
    ping_thread_instance.daemon = True
    ping_thread_instance.start()
    
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
                    if event.stream_ended:
                        headers_dict = dict(headers)
                        path = headers_dict.get(':path', '/')
                        # logging.debug(f'Path accessed: {path}')
                        stream_windows[event.stream_id] = 65535  # Initial stream flow control window size
                        stream_states[event.stream_id] = 'open' # set initial state of the stream to 'open'
                        last_stream_id = event.stream_id
                        
                        
                        # auth html file (main page)
                        if path == '/':
                            with open('templates/auth.html', 'r') as f:
                                html_content = f.read()

                            response_headers = [
                                (':status', '200'),
                                ('content-length', str(len(html_content))),
                                ('content-type', 'text/html'),
                            ]
                            
                            
                            # Check if headers exceed the maximum frame size
                            headers_size = sum(len(k) + len(v) for k, v in response_headers)
                            if headers_size > conn.max_outbound_frame_size:
                                # Send initial HEADERS frame
                                conn.send_headers(event.stream_id, response_headers[:1])
                                # Send CONTINUATION frames for the remaining headers
                                send_continuation_frame(conn, event.stream_id, response_headers[1:], 0)
                            else:
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
                    else:
                        partial_headers[event.stream_id] = headers
                        
                # Flow Control 
                elif isinstance(event, DataReceived):
                    conn.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
                    
                    # Send WINDOW_UPDATE if needed
                    if event.flow_controlled_length > 0:
                        send_window_update(conn, event.stream_id, event.flow_controlled_length)
                
                # Stream States
                elif isinstance(event, StreamEnded):
                    stream_states[event.stream_id] = 'half-closed (remote)'
                    try:
                        conn.end_stream(event.stream_id)
                    except StreamClosedError:
                        logging.info(f"Stream {event.stream_id} already closed.")
                        
                    # Process accumulated headers if any
                    if event.stream_id in partial_headers:
                        complete_headers = partial_headers.pop(event.stream_id)
                        headers_dict =  dict(complete_headers)
                        path = headers_dict.get(':path', '/')
                        # Process the request path as usual
                        if path == '/':
                            with open('templates/auth.html', 'r') as f:
                                html_content = f.read()

                            response_headers = [
                                (':status', '200'),
                                ('content-length', str(len(html_content))),
                                ('content-type', 'text/html'),
                            ]

                            # Check if headers exceed the maximum frame size
                            headers_size = sum(len(k) + len(v) for k, v in response_headers)
                            if headers_size > conn.max_outbound_frame_size:
                                # Send initial HEADERS frame
                                conn.send_headers(event.stream_id, response_headers[:1])
                                # Send CONTINUATION frames for the remaining headers
                                send_continuation_frame(conn, event.stream_id, response_headers[1:], 0)
                            else:
                                conn.send_headers(event.stream_id, response_headers)

                            connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, html_content.encode('utf-8'), connection_window, stream_windows)

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
                            response_headers = [
                                (':status', '200'),
                                ('content-length', '13'),
                                ('content-type', 'text/plain'),
                            ]
                            conn.send_headers(event.stream_id, response_headers)
                            connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'High Priority', connection_window, stream_windows)
                        elif path == '/low-priority':
                            response_headers = [
                                (':status', '200'),
                                ('content-length', '12'),
                                ('content-type', 'text/plain'),
                            ]
                            conn.send_headers(event.stream_id, response_headers)
                            connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Low Priority', connection_window, stream_windows)

                        elif path == '/authenticate':
                            auth_header = headers_dict.get('authorization', None)
                            if auth_header and ':' not in auth_header:
                                nonce = Authentication.generate_nonce()
                                response_headers = [
                                    (':status', '401'),
                                    ('www-authenticate', f'Digest realm="test", nonce="{nonce}"')
                                ]
                                conn.send_headers(event.stream_id, response_headers, end_stream=True)
                            else:
                                authenticated = Authentication.authenticate(headers_dict, nonce)
                                if not authenticated:
                                    response_headers = [
                                        (':status', '401'),
                                        ('www-authenticate', f'Digest realm="test", nonce="{nonce}"')
                                    ]
                                    conn.send_headers(event.stream_id, response_headers, end_stream=True)
                                else:
                                    response_headers = [
                                        (':status', '200'),
                                        ('content-length', '13'),
                                        ('content-type', 'text/plain'),
                                    ]
                                    conn.send_headers(event.stream_id, response_headers)
                                    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Success! :D', connection_window, stream_windows)
                    else:
                        logging.warning(f"Stream {event.stream_id} ended without receiving headers.")
                    
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
                    
                    send_rst_stream_frame(conn, event.stream_id, h2.errors.REFUSED_STREAM)
                    
                #PRIORITY frame logging
                elif isinstance(event, PriorityUpdated):
                    logging.info(f"Stream {event.stream_id} priority updated: weight={event.weight}, depends_on={event.depends_on}, exclusive={event.exclusive}")
                    stream_priorities[event.stream_id] = {
                        'weight': event.weight,
                        'depends_on': event.depends_on,
                        'exclusive': event.exclusive
                    }
                    
                    # send_priority_frame(conn, event.stream_id, event.weight, event.depends_on, event.exclusive)

                elif isinstance(event, RemoteSettingsChanged):
                    logging.info(f"Remote settings changed: {event.changed_settings}")
                    
            secure_socket.sendall(conn.data_to_send())
    except Exception as e:
        logging.error(f"Exception in handle_client: {e}")
    finally:
        
        send_goaway_frame(conn, last_stream_id)

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

    
