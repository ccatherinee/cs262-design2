import unittest
from unittest import mock
import selectors
import machine
import types


class TestServerMethods(unittest.TestCase):
    def setUp(self):
        self.messages = []

    @mock.patch("selectors.DefaultSelector")
    @mock.patch("socket.socket")
    def test_init(self, mock_socket, mock_selector):
        server = machine.Server(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        mock_socket.assert_called_once()
        mock_socket.return_value.bind.assert_called_once_with(("test_host", "test_port1"))
        mock_socket.return_value.listen.assert_called_once()
        mock_socket.return_value.setblocking.assert_called_once_with(False)
        mock_selector.assert_called_once()
        mock_selector.return_value.register.assert_called_once_with(mock_socket.return_value, selectors.EVENT_READ, data=None)
        self.assertEqual(self.messages, server.messages)
            
    @mock.patch("selectors.DefaultSelector")
    @mock.patch("socket.socket")
    def test_accept_wrapper(self, mock_socket, mock_selector):
        server = machine.Server(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        conn, addr = mock.Mock(name="conn"), mock.Mock(name="addr")
        mock_socket.return_value.accept.return_value = (conn, addr)
        server.accept_wrapper()
        mock_socket.return_value.accept.assert_called_once()
        conn.setblocking.assert_called_once_with(False)
        mock_selector.return_value.register.assert_called_with(conn, selectors.EVENT_READ, data=types.SimpleNamespace(addr=addr))

    def test_service_connection(self):
        pass

    def test_recvall(self):
        pass

    def test_run(self):
        pass


class TestClientMethods(unittest.TestCase):
    def test_init(self):
        pass

    def test_read_message(self):
        pass

    def test_write_message(self):
        pass

    def test_internal_event(self):
        pass

    def test_run(self):
        pass


if __name__ == '__main__':
    unittest.main()
