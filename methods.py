
import time

import logging
import Authentication
# from Server import encode_headers
from utils import send_continuation_frame, send_data_with_flow_control
from Cache import CacheManager, generate_etag, get_last_modified_time
from h2.exceptions import ProtocolError 
import hpack

logging.basicConfig(level=logging.DEBUG)
nonce = None
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
    logging.debug(f"Decoded headers: {encoded_headers} -> {decoded_headers}")
    decoded_size = sum(len(k) + len(v) for k, v in decoded_headers)
    logging.info(f"Encoded headers size: {len(encoded_headers)} bytes")
    logging.info(f"Decoded headers size: {decoded_size} bytes")
    return decoded_headers

def handle_request(event, conn, connection_window, stream_windows, stream_states, partial_headers, cache_manager , stream_priorities):
    global nonce
    headers = event.headers
    logging.debug(f"Handling request for stream_id={event.stream_id} with headers: {headers}")
    try:
        if event.stream_ended:
            headers_dict = dict(headers)
            path = headers_dict.get(':path', '/')
            method = headers_dict.get(':method')
            stream_windows[event.stream_id] = 65535  # Initial stream flow control window size
            stream_states[event.stream_id] = 'open'  # set initial state of the stream to 'open'
            last_stream_id = event.stream_id

            # if path == '/high-priority':
            #     stream_priorities[event.stream_id] = {'weight': 256}
            # elif path == '/low-priority':
            #     stream_priorities[event.stream_id] = {'weight': 0}
            # else:
            #     stream_priorities[event.stream_id] = {'weight': 16}

                
            if cache_manager.is_cached(path):
                cached_content = cache_manager.load_from_cache(path)
                response_headers = [
                    (':status', '200'),
                    ('content-length', str(len(cached_content))),
                    ('content-type', 'text/html'),
                    ('etag', generate_etag(cached_content)),
                    ('last-modified', get_last_modified_time(path)),
                ]
                encoded_headers = encode_headers(response_headers)
                conn.send_headers(event.stream_id, response_headers)
                Server.log_responses(f"Cached Response for stream {event.stream_id}: {response_headers}")
                connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, cached_content, connection_window, stream_windows)
            else:
                if method == 'GET':
                    handle_get_request(event, conn, connection_window, stream_windows, stream_states, partial_headers, cache_manager, path, headers_dict)
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
    except Exception as e:
        logging.error(f"Exception in handle_request: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def handle_get_request(event, conn, connection_window, stream_windows, stream_states, partial_headers, cache_manager, path, headers_dict):
    try:
        if path == '/':
            serve_auth_html(event, conn, connection_window, stream_windows,cache_manager,path)
        elif path.startswith( '/welcome'):
            serve_welcome_html(event, conn, connection_window, stream_windows,cache_manager,path)
        elif path == '/style.css':
            serve_css(event, conn, connection_window, stream_windows, cache_manager, path)
        elif path == '/high-priority':
            serve_high_priority(event, conn, connection_window, stream_windows)
        elif path == '/low-priority':
            serve_low_priority(event, conn, connection_window, stream_windows)
        elif path == '/authenticate':
            handle_authentication(event, conn, connection_window, stream_windows, headers_dict)
        else:
            send_error_response(conn, event.stream_id, 404, "Not Found")
    except Exception as e:
        logging.error(f"Exception in handle_get_request: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def serve_auth_html(event, conn, connection_window, stream_windows, cache_manager, path):
    logging.debug("Serving auth HTML")
    try:
        with open('templates/auth.html', 'rb') as f:
            html_content = f.read()
        logging.debug("Read auth.html content successfully")
    except FileNotFoundError:
        logging.error("auth.html file not found")
        send_error_response(conn, event.stream_id, 404, "Not Found")
        return
    except Exception as e:
        logging.error(f"Exception in serve_auth_html: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")
        return

    response_headers = [
        (':status', '200'),
        ('content-length', str(len(html_content))),
        ('content-type', 'text/html'),
    ]

    headers_size = sum(len(k) + len(v) for k, v in response_headers)
    if headers_size > conn.max_outbound_frame_size:
        conn.send_headers(event.stream_id, response_headers[:1])
        Server.log_responses(f"Auth HTML Response for stream {event.stream_id}: {response_headers}")
        send_continuation_frame(conn, event.stream_id, response_headers[1:], 0)
    else:
        conn.send_headers(event.stream_id, response_headers)
        Server.log_responses(f"Auth HTML Response for stream {event.stream_id}: {response_headers}")

    if event.stream_id not in stream_windows:
        stream_windows[event.stream_id] = conn.remote_settings.initial_window_size

    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, html_content, connection_window, stream_windows)
    # Save to cache
    cache_manager.save_to_cache(path, html_content)

    # Server push for style.css
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
            logging.debug(f"Sent push promise for style.css on stream {push_stream_id}")
            if cache_manager.is_cached('style.css'):
                logging.debug("Loading style.css from cache")
                css_content = cache_manager.load_from_cache('style.css')
            else:
                logging.debug("Reading style.css from disk")
                with open('templates/style.css', 'rb') as f:
                    css_content = f.read()
                cache_manager.save_to_cache('style.css', css_content)
            push_response_headers = [
                (':status', '200'),
                ('content-length', str(len(css_content))),
                ('content-type', 'text/css'),
            ]
            conn.send_headers(push_stream_id, push_response_headers)
            connection_window, stream_windows = send_data_with_flow_control(conn, push_stream_id, css_content, connection_window, stream_windows)
            logging.debug(f"Sent style.css on stream {push_stream_id}")
        except FileNotFoundError:
            logging.error("style.css file not found")
            send_error_response(conn, event.stream_id, 404, "Not Found")
        except ProtocolError:
            logging.info("Server push is disabled by the client.")
        except Exception as e:
            logging.error(f"Exception in server push: {e}")
            send_error_response(conn, event.stream_id, 500, "Internal Server Error")
    # Server push for script.js
    if conn.remote_settings.enable_push:
        try:
            push_stream_id = conn.get_next_available_stream_id()
            push_headers = [
                (':method', 'GET'),
                (':authority', 'localhost:8443'),
                (':scheme', 'https'),
                (':path', '/script.js')
            ]
            conn.push_stream(event.stream_id, push_stream_id, push_headers)
            logging.debug(f"Sent push promise for script.js on stream {push_stream_id}")
            if cache_manager.is_cached('script.js'):
                logging.debug("Loading script.js from cache")
                js_content = cache_manager.load_from_cache('script.js')
            else:
                logging.debug("Reading script.js from disk")
                with open('templates/script.js', 'rb') as f:
                    js_content = f.read()
                cache_manager.save_to_cache('script.js', js_content)
            push_response_headers = [
                (':status', '200'),
                ('content-length', str(len(js_content))),
                ('content-type', 'templates/javascript'),
            ]
            conn.send_headers(push_stream_id, push_response_headers)
            connection_window, stream_windows = send_data_with_flow_control(conn, push_stream_id, js_content, connection_window, stream_windows)
            logging.debug(f"Sent script.js on stream {push_stream_id}")
        except FileNotFoundError:
            logging.error("script.js file not found")
            send_error_response(conn, event.stream_id, 404, "Not Found")
        except ProtocolError:
            logging.info("Server push is disabled by the client.")
        except Exception as e:
            logging.error(f"Exception in server push: {e}")
            send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def serve_css(event, conn, connection_window, stream_windows, cache_manager, path):
    logging.debug("Serving CSS")
    try:
        if cache_manager.is_cached(path):
            logging.debug("Loading style.css from cache")
            css_content = cache_manager.load_from_cache(path)
        else:
            logging.debug("Reading style.css from disk")
            with open('templates/style.css', 'rb') as f:
                css_content = f.read()
            cache_manager.save_to_cache('style.css', css_content)
        response_headers = [
            (':status', '200'),
            ('content-length', str(len(css_content))),
            ('content-type', 'text/css'),
        ]
        conn.send_headers(event.stream_id, response_headers)
        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, css_content, connection_window, stream_windows)
    except FileNotFoundError:
        logging.error("style.css file not found")
        send_error_response(conn, event.stream_id, 404, "Not Found")
    except Exception as e:
        logging.error(f"Exception in serve_css: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def serve_welcome_html(event, conn, connection_window, stream_windows, cache_manager, path):
    logging.debug("Serving welcome HTML")
    try:
        with open('templates/welcome.html', 'rb') as f:
            content = f.read()
    except FileNotFoundError:
        logging.error("welcome.html file not found")
        send_error_response(conn, event.stream_id, 404, "Not Found")
        return
    except Exception as e:
        logging.error(f"Exception in serve_welcome_html: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")
        return

    response_headers = [
        (':status', '200'),
        ('content-length', str(len(content))),
        ('content-type', 'text/html'),
    ]

    headers_size = sum(len(k) + len(v) for k, v in response_headers)
    if headers_size > conn.max_outbound_frame_size:
        conn.send_headers(event.stream_id, response_headers[:1])
        send_continuation_frame(conn, event.stream_id, response_headers[1:], 0)
    else:
        conn.send_headers(event.stream_id, response_headers)

    if event.stream_id not in stream_windows:
        stream_windows[event.stream_id] = conn.remote_settings.initial_window_size

    connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, content, connection_window, stream_windows)
    # cache_manager.save_to_cache(path, content)

    # Server push for style.css
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
            logging.debug(f"Sent push promise for style.css on stream {push_stream_id}")
            if cache_manager.is_cached('style.css'):
                logging.debug("Loading style.css from cache")
                css_content = cache_manager.load_from_cache('style.css')
            else:
                logging.debug("Reading style.css from disk")
                with open('templates/style.css', 'rb') as f:
                    css_content = f.read()
                cache_manager.save_to_cache('style.css', css_content)
            push_response_headers = [
                (':status', '200'),
                ('content-length', str(len(css_content))),
                ('content-type', 'text/css'),
            ]
            conn.send_headers(push_stream_id, push_response_headers)
            connection_window, stream_windows = send_data_with_flow_control(conn, push_stream_id, css_content, connection_window, stream_windows)
            logging.debug(f"Sent style.css on stream {push_stream_id}")
        except FileNotFoundError:
            logging.error("style.css file not found")
        except ProtocolError:
            logging.info("Server push is disabled by the client.")
        except Exception as e:
            logging.error(f"Exception in server push: {e}")
            
def serve_high_priority(event, conn, connection_window, stream_windows):
    try:
        response_headers = [
            (':status', '200'),
            ('content-length', '13'),
            ('content-type', 'text/plain'),
        ]
        logging.debug(f"Serving high priority for stream_id={event.stream_id}")
        conn.send_headers(event.stream_id, response_headers)

        logging.debug(f"Sent headers for high priority: {response_headers}")
        # time.sleep(5)

        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'High Priority', connection_window, stream_windows)
        conn.end_stream(event.stream_id)
        logging.debug(f"Ended stream for high priority: {event.stream_id}")
    except Exception as e:
        logging.error(f"Exception in serve_high_priority: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def serve_low_priority(event, conn, connection_window, stream_windows):
    try:
        response_headers = [
            (':status', '200'),
            ('content-length', '12'),
            ('content-type', 'text/plain'),
        ]
        logging.debug(f"Serving low priority for stream_id={event.stream_id}")
        conn.send_headers(event.stream_id, response_headers)

        logging.debug(f"Sent headers for low priority: {response_headers}")
        # time.sleep(5)

        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Low Priority', connection_window, stream_windows)
        conn.end_stream(event.stream_id)
        logging.debug(f"Ended stream for low priority: {event.stream_id}")
    except Exception as e:
        logging.error(f"Exception in serve_low_priority: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")


def handle_authentication(event, conn, connection_window, stream_windows, headers_dict):
    global nonce
    try:
        auth_header = headers_dict.get('authorization', None)
        if auth_header and ':' not in auth_header:
            nonce = Authentication.generate_nonce()
            logging.debug(f"Generated nonce for stream_id={event.stream_id}: {nonce}")
            response_headers = [
                (':status', '401'),
                ('www-authenticate', f'Digest realm="test", nonce="{nonce}"')
            ]
            conn.send_headers(event.stream_id, response_headers, end_stream=True)
            Server.log_responses(f"Authentication Response for stream {event.stream_id}: {response_headers}")
        else:
            logging.debug(f"nonce is {nonce}")
            authenticated , username = Authentication.authenticate(headers_dict, nonce)
            logging.debug(f"Retrieved nonce for stream_id={event.stream_id}: {nonce}")
            if not authenticated:
                response_headers = [
                    (':status', '401'),
                    ('www-authenticate', f'Digest realm="test", nonce="{nonce}"')
                ]
                conn.send_headers(event.stream_id, response_headers, end_stream=True)
                Server.log_responses(f"Authentication Response for stream {event.stream_id}: {response_headers}")
            else:
                response_headers = [
                    (':status', '200'),
                    ('content-length', str(len(username))),
                    ('content-type', 'text/plain'),
                ]
                conn.send_headers(event.stream_id, response_headers)

                connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, username.encode('utf-8'), connection_window, stream_windows)

    except Exception as e:
        logging.error(f"Exception in handle_authentication: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def handle_post_request(event, conn, connection_window, stream_windows, path):
    try:
        response_headers = [
            (':status', '200'),
            ('content-length', '11'),
            ('content-type', 'text/plain'),
        ]
        conn.send_headers(event.stream_id, response_headers)
        Server.log_responses(f"POST request response: {response_headers}")
        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'POST data', connection_window, stream_windows)
    except Exception as e:
        logging.error(f"Exception in handle_post_request: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def handle_put_request(event, conn, connection_window, stream_windows, path):
    try:
        response_headers = [
            (':status', '200'),
            ('content-length', '10'),
            ('content-type', 'text/plain'),
        ]
        conn.send_headers(event.stream_id, response_headers)
        Server.log_responses(f"PUT request response: {response_headers}")
        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'PUT data', connection_window, stream_windows)
    except Exception as e:
        logging.error(f"Exception in handle_put_request: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def handle_delete_request(event, conn, connection_window, stream_windows, path):
    try:
        response_headers = [
            (':status', '200'),
            ('content-length', '7'),
            ('content-type', 'text/plain'),
        ]
        conn.send_headers(event.stream_id, response_headers)
        Server.log_responses(f"DELETE request response: {response_headers}")
        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Deleted', connection_window, stream_windows)
    except Exception as e:
        logging.error(f"Exception in handle_delete_request: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def handle_head_request(event, conn, connection_window, stream_windows, path):
    try:
        response_headers = [
            (':status', '200'),
            ('content-length', '0'),
            ('content-type', 'text/plain'),
        ]
        conn.send_headers(event.stream_id, response_headers, end_stream=True)
        Server.log_responses(f"HEAD request response: {response_headers}")
    except Exception as e:
        logging.error(f"Exception in handle_head_request: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")

def handle_options_request(event, conn, connection_window, stream_windows, path):
    try:
        response_headers = [
            (':status', '204'),
            ('allow', 'GET, POST, PUT, DELETE, HEAD, OPTIONS, PATCH'),
        ]
        conn.send_headers(event.stream_id, response_headers, end_stream=True)
        Server.log_responses(f"OPTIONS request response: {response_headers}")
    except Exception as e:
        logging.error(f"Exception in handle_options_request: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")
        
        
def handle_patch_request(event, conn, connection_window, stream_windows, path):
    try:
        response_headers = [
            (':status', '200'),
            ('content-length', '6'),
            ('content-type', 'text/plain'),
        ]
        conn.send_headers(event.stream_id, response_headers)
        Server.log_responses(f"PATCH request response: {response_headers}")
        connection_window, stream_windows = send_data_with_flow_control(conn, event.stream_id, b'Patched', connection_window, stream_windows)
    except Exception as e:
        logging.error(f"Exception in handle_patch_request: {e}")
        send_error_response(conn, event.stream_id, 500, "Internal Server Error")
        
    
def send_error_response(conn, stream_id, status_code, message):
    response_headers = [
        (':status', str(status_code)),
        ('content-length', str(len(message))),
        ('content-type', 'text/plain'),
    ]
    conn.send_headers(stream_id, response_headers)
    Server.log_responses(f"Error response: {status_code} {message}")
    conn.send_data(stream_id, message.encode('utf-8'), end_stream=True)
