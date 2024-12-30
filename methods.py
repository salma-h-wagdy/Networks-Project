


import logging
import Authentication
from utils import send_continuation_frame, send_data_with_flow_control
from Cache import CacheManager, generate_etag, get_last_modified_time
from h2.exceptions import ProtocolError 


logging.basicConfig(level=logging.DEBUG)
nonce = None

def handle_request(event, conn, connection_window, stream_windows, stream_states, partial_headers, cache_manager):
    
    # request_headers = event.headers
    # headers_dict = dict(request_headers)
    # method = headers_dict.get(':method')
    # path = headers_dict.get(':path', '/')
    
    # print (f"method used: {method}" )
    global nonce
    headers = event.headers
    if event.stream_ended:
        headers_dict = dict(headers)
        path = headers_dict.get(':path', '/')
        method = headers_dict.get(':method')
        # logging.debug(f'Path accessed: {path}')
        stream_windows[event.stream_id] = 65535  # Initial stream flow control window size
        stream_states[event.stream_id] = 'open' # set initial state of the stream to 'open'
        last_stream_id = event.stream_id
        
        if cache_manager.is_cached(path):
            cached_content = cache_manager.load_from_cache(path)
            response_headers = [
                (':status', '200'),
                ('content-length', str(len(cached_content))),
                ('content-type', 'text/html'),
                ('etag', generate_etag(cached_content)),
                ('last-modified', get_last_modified_time(path)),
            ]
            conn.send_headers(event.stream_id, response_headers)
            connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, cached_content, connection_window, stream_windows)
        else:

            if method == 'GET':
                handle_get_request(event, conn, connection_window, stream_windows, stream_states, partial_headers, cache_manager, path , headers_dict)
            elif method == 'POST':
                handle_post_request(event, conn, connection_window, stream_windows, path)
            elif method == 'PUT':
                handle_put_request(event, conn, connection_window, stream_windows, path)
            elif method == 'DELETE':
                handle_delete_request(event, conn, connection_window, stream_windows, path)
            elif method == 'HEAD':
                handle_head_request(event, conn, connection_window, stream_windows, path)
            elif method == 'OPTIONS':
                handle_options_request(event, conn, connection_window, stream_windows, path)
            elif method == 'PATCH':
                handle_patch_request(event, conn, connection_window, stream_windows, path)
            else:
                send_error_response(conn, event.stream_id, 405, "Method Not Allowed")


    else:
        partial_headers[event.stream_id] = headers
        
def handle_get_request(event, conn, connection_window, stream_windows, stream_states, partial_headers, cache_manager, path, headers_dict):
    if path == '/':
        serve_auth_html(event, conn, connection_window, stream_windows)
    elif path == '/high-priority':
        serve_high_priority(event, conn, connection_window, stream_windows)
    elif path == '/low-priority':
        serve_low_priority(event, conn, connection_window, stream_windows)
    elif path == '/authenticate':
        handle_authentication(event, conn, connection_window, stream_windows, headers_dict)
    else:
        send_error_response(conn, event.stream_id, 404, "Not Found")

def serve_auth_html(event, conn, connection_window, stream_windows):
    logging.debug("Serving auth HTML")
    try:
        with open('templates/auth.html', 'r') as f:
            html_content = f.read()
        logging.debug("Read auth.html content successfully")
    except FileNotFoundError:
        logging.error("auth.html file not found")
        send_error_response(conn, event.stream_id, 404, "Not Found")
        return

    response_headers = [
        (':status', '200'),
        ('content-length', str(len(html_content))),
        ('content-type', 'text/html'),
    ]

    headers_size = sum(len(k) + len(v) for k, v in response_headers)
    if headers_size > conn.max_outbound_frame_size:
        conn.send_headers(event.stream_id, response_headers[:1])
        send_continuation_frame(conn, event.stream_id, response_headers[1:], 0)
    else:
        conn.send_headers(event.stream_id, response_headers)

    # Ensure stream_windows is updated
    if event.stream_id not in stream_windows:
        stream_windows[event.stream_id] = conn.remote_settings.initial_window_size

    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, html_content.encode('utf-8'), connection_window, stream_windows)

    # Server push
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
            with open('templates/style.css', 'r') as f:
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

def serve_high_priority(event, conn, connection_window, stream_windows):
    response_headers = [
        (':status', '200'),
        ('content-length', '13'),
        ('content-type', 'text/plain'),
    ]
    conn.send_headers(event.stream_id, response_headers)
    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'High Priority', connection_window, stream_windows)

def serve_low_priority(event, conn, connection_window, stream_windows):
    response_headers = [
        (':status', '200'),
        ('content-length', '12'),
        ('content-type', 'text/plain'),
    ]
    conn.send_headers(event.stream_id, response_headers)
    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Low Priority', connection_window, stream_windows)

def handle_authentication(event, conn, connection_window, stream_windows, headers_dict):
    global nonce
    auth_header = headers_dict.get('authorization', None)
    if auth_header and ':' not in auth_header:
        nonce = Authentication.generate_nonce()
        logging.debug(f"Generated nonce for stream_id={event.stream_id}: {nonce}")
        response_headers = [
            (':status', '401'),
            ('www-authenticate', f'Digest realm="test", nonce="{nonce}"')
        ]
        conn.send_headers(event.stream_id, response_headers, end_stream=True)
    else:
        logging.debug(f"nonce is {nonce}")
        authenticated = Authentication.authenticate(headers_dict, nonce)
        logging.debug(f"Retrieved nonce for stream_id={event.stream_id}: {nonce}")
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
    
                    

def handle_post_request(event, conn, connection_window, stream_windows, path):
    response_headers = [
        (':status', '200'),
        ('content-length', '11'),
        ('content-type', 'text/plain'),
    ]
    conn.send_headers(event.stream_id, response_headers)
    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'POST data', connection_window, stream_windows)

def handle_put_request(event, conn, connection_window, stream_windows, path):
    # Handle PUT request
    response_headers = [
        (':status', '200'),
        ('content-length', '10'),
        ('content-type', 'text/plain'),
    ]
    conn.send_headers(event.stream_id, response_headers)
    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'PUT data', connection_window, stream_windows)

def handle_delete_request(event, conn, connection_window, stream_windows, path):
    # Handle DELETE request
    response_headers = [
        (':status', '200'),
        ('content-length', '7'),
        ('content-type', 'text/plain'),
    ]
    conn.send_headers(event.stream_id, response_headers)
    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Deleted', connection_window, stream_windows)

def handle_head_request(event, conn, connection_window, stream_windows, path):
    # Handle HEAD request
    response_headers = [
        (':status', '200'),
        ('content-length', '0'),
        ('content-type', 'text/plain'),
    ]
    conn.send_headers(event.stream_id, response_headers, end_stream=True)

def handle_options_request(event, conn, connection_window, stream_windows, path):
    # Handle OPTIONS request
    response_headers = [
        (':status', '204'),
        ('allow', 'GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH'),
    ]
    conn.send_headers(event.stream_id, response_headers, end_stream=True)

def handle_patch_request(event, conn, connection_window, stream_windows, path):
    # Handle PATCH request
    response_headers = [
        (':status', '200'),
        ('content-length', '6'),
        ('content-type', 'text/plain'),
    ]
    conn.send_headers(event.stream_id, response_headers)
    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Patched', connection_window, stream_windows)

def send_error_response(conn, stream_id, status_code, message):
    response_headers = [
        (':status', str(status_code)),
        ('content-length', str(len(message))),
        ('content-type', 'text/plain'),
    ]
    conn.send_headers(stream_id, response_headers)
    conn.send_data(stream_id, message.encode('utf-8'), end_stream=True)
