import threading
import unittest
from unittest.mock import Mock, patch
from methods import handle_request, serve_auth_html, serve_high_priority, serve_low_priority

class TestHandleRequest(unittest.TestCase):

    def setUp(self):
        self.conn = Mock()
        self.conn.max_outbound_frame_size = 16384  # Mock the max_outbound_frame_size
        self.event = Mock()
        self.connection_window = 65535
        self.stream_windows = {}
        self.stream_states = {}
        self.partial_headers = {}
        self.cache_manager = Mock()
        self.cached_content = b"cached content"
        self.cache_manager.load_from_cache.return_value = self.cached_content

    def test_handle_get_request(self):
        self.event.headers = [(':method', 'GET'), (':path', '/')]
        self.event.stream_ended = True
        self.cache_manager.is_cached.return_value = False

        handle_request(self.event, self.conn, self.connection_window, self.stream_windows, self.stream_states, self.partial_headers, self.cache_manager)

        self.conn.send_headers.assert_called()
        self.conn.send_data.assert_called()

    def test_handle_post_request(self):
        self.event.headers = [(':method', 'POST'), (':path', '/')]
        self.event.stream_ended = True

        handle_request(self.event, self.conn, self.connection_window, self.stream_windows, self.stream_states, self.partial_headers, self.cache_manager)

        self.conn.send_headers.assert_called()
        self.conn.send_data.assert_called()

    def test_handle_put_request(self):
        self.event.headers = [(':method', 'PUT'), (':path', '/')]
        self.event.stream_ended = True

        handle_request(self.event, self.conn, self.connection_window, self.stream_windows, self.stream_states, self.partial_headers, self.cache_manager)

        self.conn.send_headers.assert_called()
        self.conn.send_data.assert_called()

    def test_handle_delete_request(self):
        self.event.headers = [(':method', 'DELETE'), (':path', '/')]
        self.event.stream_ended = True

        handle_request(self.event, self.conn, self.connection_window, self.stream_windows, self.stream_states, self.partial_headers, self.cache_manager)

        self.conn.send_headers.assert_called()
        self.conn.send_data.assert_called()

    def test_handle_head_request(self):
        self.event.headers = [(':method', 'HEAD'), (':path', '/')]
        self.event.stream_ended = True

        handle_request(self.event, self.conn, self.connection_window, self.stream_windows, self.stream_states, self.partial_headers, self.cache_manager)

        self.conn.send_headers.assert_called()

    def test_handle_options_request(self):
        self.event.headers = [(':method', 'OPTIONS'), (':path', '/')]
        self.event.stream_ended = True

        handle_request(self.event, self.conn, self.connection_window, self.stream_windows, self.stream_states, self.partial_headers, self.cache_manager)

        self.conn.send_headers.assert_called()

    def test_handle_patch_request(self):
        self.event.headers = [(':method', 'PATCH'), (':path', '/')]
        self.event.stream_ended = True

        handle_request(self.event, self.conn, self.connection_window, self.stream_windows, self.stream_states, self.partial_headers, self.cache_manager)

        self.conn.send_headers.assert_called()
        self.conn.send_data.assert_called()

    def test_serve_auth_html_with_large_headers(self):
        self.event.stream_id = 1
        self.conn.remote_settings.initial_window_size = 65535
        self.conn.remote_settings.enable_push = False

        #   return a large HTML content
        with patch('builtins.open', unittest.mock.mock_open(read_data='a' * 1000)):
            serve_auth_html(self.event, self.conn, self.connection_window, self.stream_windows)

        # check if continuation frames were used
        self.conn.send_headers.assert_called()
        self.conn.send_data.assert_called()
        self.conn.send_headers.assert_any_call(self.event.stream_id, unittest.mock.ANY)
        self.conn.send_data.assert_any_call(self.event.stream_id, unittest.mock.ANY)

    def test_prioritization(self):
        def high_priority_request():
            serve_high_priority(self.event_high, self.conn, self.connection_window, self.stream_windows)

        def low_priority_request():
            serve_low_priority(self.event_low, self.conn, self.connection_window, self.stream_windows)

        # Create threads for high and low priority requests
        high_priority_thread = threading.Thread(target=high_priority_request)
        low_priority_thread = threading.Thread(target=low_priority_request)

        # Start both threads
        high_priority_thread.start()
        low_priority_thread.start()

        # Wait for both threads to complete
        high_priority_thread.join()
        low_priority_thread.join()

        # Check if both requests were handled
        self.conn.send_headers.assert_any_call(self.event_high.stream_id, unittest.mock.ANY)
        self.conn.send_headers.assert_any_call(self.event_low.stream_id, unittest.mock.ANY)
        self.conn.send_data.assert_any_call(self.event_high.stream_id, unittest.mock.ANY)
        self.conn.send_data.assert_any_call(self.event_low.stream_id, unittest.mock.ANY)


if __name__ == '__main__':
    unittest.main()