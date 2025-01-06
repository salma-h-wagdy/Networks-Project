import unittest
from unittest.mock import Mock, patch
from methods import handle_request

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

if __name__ == '__main__':
    unittest.main()