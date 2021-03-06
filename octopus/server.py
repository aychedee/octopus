# Copyright (c) 2013, Hansel Dunlop.
# License, see LICENSE for details

import os
import select
import socket


class SocketConnection(object):
    def __init__(self, socket, address):
        self._socket = socket
        self.address = address

    def __unicode__(self):
        return 'Client Connection from %s' % (self.address,)
    __str__ = __unicode__

    def connect(self):
        pass

    def receive(self, data):
        pass

    def send(self, data):
        self._socket.send(data)

    def close(self):
        pass


class  Octopus(object):

    def __init__(self, connection_type, family=socket.AF_INET):
        self.CLIENT_SOCKETS = {}
        self.BACKLOG = 5
        self.READ_SIZE = 4096
        self._connection_type = connection_type
        self.active = True
        self.serversocket = socket.socket(family, socket.SOCK_STREAM)
        self.serversocket.setsockopt(
            socket.SOL_SOCKET,  socket.SO_REUSEADDR, 1
        )
        self.serversocket.setblocking(0)
        self.server_fd = self.serversocket.fileno()
        self.epoll = select.epoll()

    def listen(self, binding_location):
        if self.serversocket.family == socket.AF_INET:
            address = (socket.gethostname(), binding_location)
        else:
            address = binding_location

        try:
            self.serversocket.bind(address)
        except socket.error as exc:
            if exc.errno == os.errno.EADDRINUSE:
                os.unlink(address)
                self.serversocket.bind(address)
            else:
                raise
        self.serversocket.listen(self.BACKLOG)
        self.epoll.register(
            self.serversocket.fileno(),
            select.EPOLLIN | select.EPOLLHUP
        )

    def start(self):
        while True:
            events = self.epoll.poll()
            for fd, event in events:
                self.route_raw_event(fd, event)

            if not self.active:
                break

    def stop(self):
        self.epoll.unregister(self.server_fd)
        self.active = False

    def route_raw_event(self, fd, event):
        if event & select.EPOLLHUP:
            if fd == self.server_fd:
                self.stop()
            else:
                self.close_client_connection(fd)

        elif fd == self.server_fd:
            self.handle_new_client_connection()
        else:
            self.handle_input_from_client(fd)

    def handle_new_client_connection(self):
        clientsocket, address = self.serversocket.accept()
        clientsocket.setblocking(0)
        connection = self._connection_type(clientsocket, address)
        self.CLIENT_SOCKETS[clientsocket.fileno()] = connection
        self.epoll.register(clientsocket.fileno(),
            select.EPOLLIN | select.EPOLLHUP
        )
        connection.connect()

    def handle_input_from_client(self, fd):
        connection = self.CLIENT_SOCKETS[fd]
        connection.receive(connection._socket.recv(self.READ_SIZE))

    def close_client_connection(self, fd):
        self.epoll.unregister(fd)
        self.CLIENT_SOCKETS[fd].close()

