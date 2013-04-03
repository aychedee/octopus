Octopus
=======

Octopus is an asynchronous socket server for the linux environment

It is ideal for providing local services over a Unix Domain Socket or to 
anywhere using an inet socket.

You initialise the server with a connection object which contains the
application logic and routing. 

Code example: A server that echoes any message sent to it out to all open
connections

    from octopus import AsyncSocketServer, SocketConnection

    class EchoConnection(SocketConnection):
        
        connections = []

        def connect(self):
            self.connections.append(self)

        def receive(self, message):
            for connection in self.connections:
                connection.send(message)
        
        if __main__ == '__main__':
            server = AsyncSocketServer(EchoConnection)
            server.listen(9876)
            server.start()

The server will listen on port 9876 any connected socket can send a message
and all connections will recieve a copy of that message
    
