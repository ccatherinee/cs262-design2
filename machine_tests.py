import unittest
from unittest import mock
import selectors
import machine
import types
import socket

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

    @mock.patch("struct.unpack")
    @mock.patch("machine.Server.recvall")
    @mock.patch("selectors.DefaultSelector")
    @mock.patch("socket.socket")
    def test_service_connection_first_new_message_in_queue(self, mock_socket, mock_selector, mock_recvall, mock_unpack):
        server = machine.Server(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        key = mock.Mock(name="key")
        mock_unpack.return_value = (123, )
        server.service_connection(key, mock.ANY)
        mock_recvall.assert_called_once_with(key.fileobj, 4)
        self.assertEqual(self.messages, [123])

    @mock.patch("struct.unpack")
    @mock.patch("machine.Server.recvall")
    @mock.patch("selectors.DefaultSelector")
    @mock.patch("socket.socket")
    def test_service_connection_multiple_messages_in_queue(self, mock_socket, mock_selector, mock_recvall, mock_unpack):
        self.messages = [123, 456, 789]
        server = machine.Server(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        key = mock.Mock(name="key")
        mock_unpack.return_value = (13790, )
        server.service_connection(key, mock.ANY)
        mock_recvall.assert_called_once_with(key.fileobj, 4)
        self.assertEqual(self.messages, [123, 456, 789, 13790])

    @mock.patch("selectors.DefaultSelector")
    @mock.patch("socket.socket")
    def test_recvall_one_iteration(self, mock_socket, mock_selector):
        server = machine.Server(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        mock_sock = mock.Mock(name="sock")
        return_values = {24: bytearray("This is a test sentence.", 'utf-8')}
        mock_sock.recv.side_effect = return_values.get
        data = server.recvall(mock_sock, 24)
        self.assertEqual(data, bytearray("This is a test sentence.", 'utf-8'))
        self.assertEqual(mock_sock.recv.call_args_list, [mock.call(24)])

    @mock.patch("selectors.DefaultSelector")
    @mock.patch("socket.socket")
    def test_recvall_multiple_iterations(self, mock_socket, mock_selector):
        server = machine.Server(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        mock_sock = mock.Mock(name="sock")
        mock_sock.recv.side_effect = {24: bytearray("This", 'utf-8'), 20: bytearray(" is", 'utf-8'), 17: bytearray(" a", 'utf-8'), 15: bytearray(" test sentence.", 'utf-8')}.get
        data = server.recvall(mock_sock, 24)
        self.assertEqual(data, bytearray("This is a test sentence.", 'utf-8'))
        self.assertEqual(mock_sock.recv.call_args_list, [mock.call(24), mock.call(20), mock.call(17), mock.call(15)])

    @mock.patch("selectors.DefaultSelector")
    @mock.patch("socket.socket")
    def test_recvall_zero_bytes(self, mock_socket, mock_selector):
        server = machine.Server(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        mock_sock = mock.Mock(name="sock")
        data = server.recvall(mock_sock, 0)
        self.assertEqual(data, bytearray())
        mock_sock.recv.assert_not_called()


class TestClientMethods(unittest.TestCase):
    def setUp(self):
        self.messages = []

    @mock.patch("socket.socket")
    def test_init(self, mock_socket):
        mock_sock1, mock_sock2 = mock.Mock(name="sock1"), mock.Mock(name="sock2")
        mock_socket.side_effect = [mock_sock1, mock_sock2]
        client = machine.Client(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        mock_socket.has_calls([(socket.AF_INET, socket.SOCK_STREAM), (socket.AF_INET, socket.SOCK_STREAM)])
        mock_sock1.setblocking.assert_called_once_with(True)
        mock_sock2.setblocking.assert_called_once_with(True)
        mock_sock1.connect.assert_called_once_with(("test_host", "test_port2"))
        mock_sock2.connect.assert_called_once_with(("test_host", "test_port3"))
        self.assertEqual(self.messages, client.messages)
        self.assertEqual(["test_host", "test_port1", "test_port2", "test_port3"], client.config)
        self.assertDictEqual({"test_port2": mock_sock1, "test_port3": mock_sock2}, client.connections)
        self.assertEqual(0, client.logical_clock)
        self.assertTrue(client.tick in range(1, 7))

    @mock.patch("socket.socket")
    def test_read_message_no_messages_in_queue(self, mock_socket):
        mock_sock1, mock_sock2 = mock.Mock(name="sock1"), mock.Mock(name="sock2")
        mock_socket.side_effect = [mock_sock1, mock_sock2]
        client = machine.Client(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        with mock.patch("builtins.open", mock.mock_open(read_data="data")) as mock_file:
            self.assertFalse(client.read_message())
            self.assertEqual(0, client.logical_clock)
            self.assertEqual([], mock_file.mock_calls)
            self.assertEqual([], self.messages)

    @mock.patch("socket.socket")
    def test_read_message_1_message_in_queue_updates_clock(self, mock_socket):
        self.messages = [123]
        mock_sock1, mock_sock2 = mock.Mock(name="sock1"), mock.Mock(name="sock2")
        mock_socket.side_effect = [mock_sock1, mock_sock2]
        client = machine.Client(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        client.logical_clock = 64
        with mock.patch("builtins.open", mock.mock_open(read_data="data")) as mock_file:
            self.assertTrue(client.read_message())
            self.assertEqual(124, client.logical_clock)
            self.assertIn(mock.call('logtest_port1.txt', 'a+'), mock_file.mock_calls)
            self.assertIn(mock.call().write(mock.ANY), mock_file.mock_calls)
            self.assertEqual([], self.messages)

    @mock.patch("socket.socket")
    def test_read_message_1_message_in_queue_updates_clock(self, mock_socket):
        self.messages = [123]
        mock_sock1, mock_sock2 = mock.Mock(name="sock1"), mock.Mock(name="sock2")
        mock_socket.side_effect = [mock_sock1, mock_sock2]
        client = machine.Client(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        client.logical_clock = 64
        with mock.patch("builtins.open", mock.mock_open(read_data="data")) as mock_file:
            self.assertTrue(client.read_message())
            self.assertEqual(124, client.logical_clock)
            self.assertIn(mock.call('logtest_port1.txt', 'a+'), mock_file.mock_calls)
            self.assertIn(mock.call().write(mock.ANY), mock_file.mock_calls)
            self.assertEqual([], self.messages)

    @mock.patch("socket.socket")
    def test_read_message_multiple_messages_in_queue_updates_clock(self, mock_socket):
        self.messages = [125, 456, 789]
        mock_sock1, mock_sock2 = mock.Mock(name="sock1"), mock.Mock(name="sock2")
        mock_socket.side_effect = [mock_sock1, mock_sock2]
        client = machine.Client(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        client.logical_clock = 12
        with mock.patch("builtins.open", mock.mock_open(read_data="data")) as mock_file:
            self.assertTrue(client.read_message())
            self.assertEqual(126, client.logical_clock)
            self.assertIn(mock.call('logtest_port1.txt', 'a+'), mock_file.mock_calls)
            self.assertIn(mock.call().write(mock.ANY), mock_file.mock_calls)
            self.assertEqual([456, 789], self.messages)

    @mock.patch("socket.socket")
    def test_read_message_multiple_messages_in_queue_no_external_clock_update(self, mock_socket):
        self.messages = [456, 778]
        mock_sock1, mock_sock2 = mock.Mock(name="sock1"), mock.Mock(name="sock2")
        mock_socket.side_effect = [mock_sock1, mock_sock2]
        client = machine.Client(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        client.logical_clock = 1234
        with mock.patch("builtins.open", mock.mock_open(read_data="data")) as mock_file:
            self.assertTrue(client.read_message())
            self.assertEqual(1235, client.logical_clock)
            self.assertIn(mock.call('logtest_port1.txt', 'a+'), mock_file.mock_calls)
            self.assertIn(mock.call().write(mock.ANY), mock_file.mock_calls)
            self.assertEqual([778], self.messages)

    @mock.patch("struct.pack")
    @mock.patch("socket.socket")
    def test_write_message(self, mock_socket, mock_pack):
        mock_sock1, mock_sock2 = mock.Mock(name="sock1"), mock.Mock(name="sock2")
        mock_socket.side_effect = [mock_sock1, mock_sock2]
        client = machine.Client(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        client.logical_clock = 261
        with mock.patch("builtins.open", mock.mock_open(read_data="data")) as mock_file:
            client.write_message("test_port2")
            self.assertEqual(262, client.logical_clock)
            mock_sock1.sendall.assert_called_once_with(mock_pack.return_value)
            self.assertIn(mock.call('logtest_port1.txt', 'a+'), mock_file.mock_calls)
            self.assertIn(mock.call().write(mock.ANY), mock_file.mock_calls)
            self.assertEqual([], self.messages)

    @mock.patch("struct.pack")
    @mock.patch("socket.socket")
    def test_internal_event(self, mock_socket, mock_pack):
        mock_sock1, mock_sock2 = mock.Mock(name="sock1"), mock.Mock(name="sock2")
        mock_socket.side_effect = [mock_sock1, mock_sock2]
        client = machine.Client(config=["test_host", "test_port1", "test_port2", "test_port3"], messages=self.messages)
        client.logical_clock = 278
        with mock.patch("builtins.open", mock.mock_open(read_data="data")) as mock_file:
            client.internal_event()
            self.assertEqual(279, client.logical_clock)
            self.assertIn(mock.call('logtest_port1.txt', 'a+'), mock_file.mock_calls)
            self.assertIn(mock.call().write(mock.ANY), mock_file.mock_calls)
            self.assertEqual([], self.messages) 


if __name__ == '__main__':
    unittest.main()
