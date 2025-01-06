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
from Cache import CacheManager, generate_etag, get_last_modified_time
import Authentication
import hpack

from methods import handle_request
from utils import send_continuation_frame, send_data_with_flow_control


logging.basicConfig(level=logging.DEBUG)
connected_clients = []
# Initialize CacheManager
cache_manager = CacheManager()





def server_status():
    while True:
        command = input("Enter 'status' to see the server status: ")
        if command == 'status':
            print(f"Number of connected clients: {len(connected_clients)}")
            
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

def is_connection_closed(conn):
    return conn.state_machine.state == h2.connection.ConnectionState.CLOSED

def ping_thread(conn):
    while True:
        time.sleep(30)  # send a PING every 30 seconds
        if is_connection_closed(conn):
            logging.info("Connection is closed, stopping ping thread.")
            break
        send_ping_frame(conn)        
   

def send_rst_stream_frame(conn, stream_id, error_code):
    conn.reset_stream(stream_id, error_code)
    logging.info(f"Sent RST_STREAM frame: stream_id={stream_id}, error_code={error_code}")
    
def send_settings_frame(conn, settings):
    conn.update_settings(settings)
    logging.info(f"Sent SETTINGS frame: {settings}")
    
def handle_invalid_frame_in_stream_state(conn, stream_id, frame_type):
    logging.error(f"Invalid frame {frame_type} received in current stream state for stream {stream_id}")
    send_rst_stream_frame(conn, stream_id, h2.errors.PROTOCOL_ERROR)
    
# def handle_invalid_frame_in_connection_state(conn, frame_type):
#     logging.error(f"Invalid frame {frame_type} received in current connection state")
#     send_goaway_frame(conn, 0, h2.errors.PROTOCOL_ERROR)
    
# def handle_invalid_frame(conn, frame_type):
#     logging.error(f"Invalid frame {frame_type} received")
#     send_goaway_frame(conn, 0, h2.errors.PROTOCOL_ERROR)
    
def prioritise_streams(stream_events, stream_priorities):
    for event in stream_events:
        if isinstance(event, RequestReceived):
            headers_dict = dict(event.headers)
            path = headers_dict.get(':path', '/')
            
            if path == '/high-priority':
                stream_priorities[event.stream_id] = {'weight': 256}
            elif path == '/low-priority':
                stream_priorities[event.stream_id] = {'weight': 0}
            else:
                stream_priorities[event.stream_id] = {'weight': 16}
        logging.info(f"Stream priorities: {stream_priorities}")

    stream_events.sort(key=lambda event: (stream_priorities.get(event.stream_id, {}).get('weight', 16), event.stream_id), reverse=True)
    return stream_events
            
 

    
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
            
            # separate connection-level events)
            connection_events = [event for event in events if not hasattr(event, 'stream_id')]
            stream_events = [event for event in events if hasattr(event, 'stream_id')]
            
            # # sort stream-level events by priority
            stream_events = prioritise_streams(stream_events, stream_priorities)
            
            for event in connection_events:
                logging.debug(f"Connection-level event received: {event}")
                
                if isinstance(event, RemoteSettingsChanged):
                    logging.info(f"Remote settings changed: {event.changed_settings}")
                
                # SETTINGS frame
                elif isinstance(event, SettingsAcknowledged):
                    logging.info("Settings acknowledged by the client.")
            
            for event in stream_events:
                
                logging.debug(f"Event received: {event}")
                if isinstance(event, RequestReceived):
                    handle_request(event, conn, connection_window, stream_windows, stream_states, partial_headers, cache_manager, stream_priorities)
                           
                # Flow Control 
                elif isinstance(event, DataReceived):
                    if stream_states.get(event.stream_id) in ['half-closed (local)', 'closed']:
                        handle_invalid_frame_in_stream_state(conn, event.stream_id, 'DATA')
                    else:
                        conn.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
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
                        handle_request(event, conn, connection_window, stream_windows, stream_states, partial_headers, cache_manager, stream_priorities)
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
                
                # # SETTINGS frame
                # elif isinstance(event, SettingsAcknowledged):
                #     logging.info("Settings acknowledged by the client.")
                    
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


                # elif isinstance(event, RemoteSettingsChanged):
                #     logging.info(f"Remote settings changed: {event.changed_settings}")
                    
            secure_socket.sendall(conn.data_to_send())
    except Exception as e:
        logging.error(f"Exception in handle_client: {e}")
    finally:
        
        send_goaway_frame(conn, last_stream_id)

        # connected_clients.remove(client_socket)
        try:
            secure_socket.close()
        except Exception as e:
            logging.error(f"Exception while closing secure_socket: {e}")
        try:
            client_socket.close()
        except Exception as e:
            logging.error(f"Exception while closing client_socket: {e}")


    
