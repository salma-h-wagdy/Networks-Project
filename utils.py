import logging
logging.basicConfig(level=logging.DEBUG)


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


# Handle CONTINUATION frames for large headers
def send_continuation_frame(conn, stream_id, headers, offset, max_frame_size=16384):
    while offset < len(headers):
        remaining = len(headers) - offset
        chunk = headers[offset:offset + max_frame_size]
        conn.send_continuation(stream_id, chunk, end_stream=False if remaining > max_frame_size else True)
        offset += max_frame_size
    logging.info(f"Sent CONTINUATION frame for stream {stream_id}, header size: {len(headers)}")
 