from mock import call, Mock, patch
import os
import select
import socket
import shutil
import tempfile
import unittest

from octopus import AsyncSocketServer


class MockSocket(object):

    def __init__(self, fd):
        self.fd = fd
        self.blocking = True

    def fileno(self):
        return self.fd

    def setblocking(self, blocking):
        self.blocking = bool(blocking)


class AsyncSocketServerTest(unittest.TestCase):

    ConnectionClass = type('ConnectionClass', (object,), {})

    def setUp(self):
        self.s = AsyncSocketServer(self.ConnectionClass)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch('octopus.server.socket.socket')
    def test_init(self, mock_socket):
        self.s = AsyncSocketServer(self.ConnectionClass)

        self.assertEqual(
            mock_socket.call_args_list,
            [call(socket.AF_INET, socket.SOCK_STREAM)]
        )
        self.assertTrue(self.s.active)
        self.assertTrue(self.s._connection_type, self.ConnectionClass)
        self.assertEqual(self.s.server_fd, self.s.serversocket.fileno())
        self.assertEqual(self.s.serversocket, mock_socket.return_value)
        self.assertEqual(self.s.serversocket.setblocking.call_args_list, [call(0)])
        self.assertEqual(type(self.s.epoll), type(select.epoll()))

    @patch('octopus.server.socket.socket')
    def test_init_default_socket_type_can_be_overriden(self, mock_socket):
        self.s = AsyncSocketServer(self.ConnectionClass, family=socket.AF_UNIX)

        self.assertTrue(self.s.serversocket.family, socket.AF_UNIX)
        self.assertTrue(self.s._connection_type, self.ConnectionClass)
        self.assertEqual(self.s.server_fd, self.s.serversocket.fileno())
        self.assertEqual(self.s.serversocket, mock_socket.return_value)
        self.assertEqual(self.s.serversocket.setblocking.call_args_list, [call(0)])
        self.assertEqual(type(self.s.epoll), type(select.epoll()))

    def test_client_socket_is_per_server_instance(self):
        ConnectionClass = type('ConnectionClass', (object,), {})

        s1 = AsyncSocketServer(ConnectionClass)
        s2 = AsyncSocketServer(ConnectionClass)
        s1.CLIENT_SOCKETS[2] = 'socket'

        self.assertNotIn(2, s2.CLIENT_SOCKETS)

    def test_listen_binds_to_port_listens_and_registers(self):
        PORT = 9999
        fd = self.s.serversocket.fileno()
        # Need to stash the socket or it gets garbage collected next line
        old_socket = self.s.serversocket
        self.s.serversocket = Mock()
        self.s.serversocket.family = socket.AF_INET
        self.s.serversocket.fileno.return_value = fd

        self.s.listen(PORT)

        self.assertEqual(
            self.s.serversocket.bind.call_args_list,
            [call((socket.gethostname(), PORT))]
        )
        self.assertEqual(
            self.s.serversocket.listen.call_args_list, [call(self.s.BACKLOG)]
        )
        self.assertRaises(
            IOError, self.s.epoll.register, fd, select.EPOLLIN
        )

    def test_listen_binds_to_uds_socket_for_af_unix_sockets(self):
        self.s = AsyncSocketServer(self.ConnectionClass, family=socket.AF_UNIX)
        uds_socket_path = os.path.join(self.temp_dir, 'uds_socket')
        fd = self.s.serversocket.fileno()
        # Need to stash the socket or it gets garbage collected next line
        old_socket = self.s.serversocket
        self.s.serversocket = Mock()
        self.s.serversocket.fileno.return_value = fd

        self.s.listen(uds_socket_path)

        self.assertEqual(
            self.s.serversocket.bind.call_args_list,
            [call(uds_socket_path)]
        )
        self.assertEqual(
            self.s.serversocket.listen.call_args_list, [call(self.s.BACKLOG)]
        )
        self.assertRaises(
            IOError, self.s.epoll.register, fd, select.EPOLLIN
        )


    @patch('octopus.AsyncSocketServer.route_raw_event')
    def test_start(self, mock_route_raw_event):
        self.s.active = False
        PORT = 9999
        self.s.listen(PORT)
        self.s.epoll = Mock()
        self.s.epoll.poll.return_value = [(self.s.server_fd, select.EPOLLIN)]
        self.s.serversocket = Mock()
        self.s.serversocket.accept.return_value = (Mock(), '123.123.123.123')

        self.s.start()

        self.assertEqual(
            mock_route_raw_event.call_args_list,
            [call(self.s.server_fd, select.EPOLLIN)]
        )

    @patch('octopus.AsyncSocketServer.handle_new_client_connection')
    def test_route_event_from_serversocket(self, mock_handle_client_conn):
        self.s.serversocket = Mock()

        self.s.route_raw_event(self.s.server_fd, select.EPOLLIN)

        self.assertTrue(mock_handle_client_conn.called)

    @patch('octopus.AsyncSocketServer.handle_input_from_client')
    def test_route_event_from_client_socket(self, mock_handle_client_input):
        self.s.serversocket = Mock()

        self.s.route_raw_event(9, select.EPOLLIN)

        self.assertEqual(mock_handle_client_input.call_args_list, [call(9)])

    def test_handle_new_client_connection(self):
        self.s.serversocket = Mock()
        address =  '123.123.123.123'
        self.s.epoll = Mock()
        mock_client_socket = MockSocket(7)
        mock_connection_class = Mock()
        self.s._connection_type = mock_connection_class
        self.s.serversocket.accept.return_value = (mock_client_socket, address)

        self.s.handle_new_client_connection()

        self.assertTrue(self.s.serversocket.accept.called)
        self.assertEqual(
            self.s.CLIENT_SOCKETS[7],
            mock_connection_class.return_value
        )
        self.assertEqual(
                mock_connection_class.call_args_list,
                [call(mock_client_socket, address)]
        )
        self.assertFalse(mock_client_socket.blocking)
        self.assertEqual(
            self.s.epoll.register.call_args_list, [call(7, select.EPOLLIN)]
        )
        self.assertTrue(mock_connection_class.return_value.connect.called)


    def test_handle_event_from_clientsocket(self):
        mock_connection = Mock()
        self.s.CLIENT_SOCKETS[9] = mock_connection

        self.s.handle_input_from_client(9)

        self.assertEqual(
            mock_connection.receive.call_args_list,
            [call(mock_connection._socket.recv.return_value)]
        )
        self.assertEqual(
            mock_connection._socket.recv.call_args_list,
            [call(self.s.READ_SIZE)]
        )
