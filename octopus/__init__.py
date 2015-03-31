"""
Octopus is an asynchronous socket server for the linux environment

                        .-'   `'.
                       /         \
                       |         ;
                       |         |           ___.--,
              _.._     |0) ~ (0) |    _.---'`__.-( (_.
       __.--'`_.. '.__.\    '--. \_.-' ,.--'`     `""`
      ( ,.--'`   ',__ /./;   ;, '.__.'`    __
     _`) )  .---.__.' / |   |\   \__..--""  "'"--.,_
     `---' .'.''-._.-'`_./  /\ '.  \ _.-~~~````~~~-._`-.__.'
           | |  .' _.-' |  |  \  \  '.               `~---`
                \ \/ .'     \  \   '. '-._)
                 \/ /        \  \    `=.__`~-.
            jgs  / /\         `) )    / / `"".`\
           , _.-'.'\ \        / /    ( (     / /
            `--~`   ) )    .-'.'      '.'.  | (
                   (/`    ( (`          ) )  '-;
                    `      '-;         (-'

Code example: A server that echoes any message sent to it out to all open
connections

    from octopus import Octopus, SocketConnection

    class EchoConnection(SocketConnection):

        connections = []

        def connect(self):
            self.connections.append(self)

        def receive(self, message):
            for connection in self.connections:
                connection.send(message)

        if __main__ == '__main__':
            octopus = Octopus(EchoConnection)
            octopus.listen(9876)
            octopus.start()


The server will listen on port 9876 any connected socket can send a message
and all connections will recieve a copy of that message

Copyright (c) 2015, Hansel Dunlop.
License, see LICENSE for details
"""

__title__ = 'octopus'
__version__ = '0.1'
__author__ = 'Hansel Dunlop'
__license__ = 'Permissive, see LICENSE'
__copyright__ = 'Copyright 2013 Hansel Dunlop'

from .server import Octopus, SocketConnection
