#
# Synchronized publisher. This is like a metlog cliennt
#
import zmq
import Queue
import sys
from contextlib import contextmanager

class Client(object):
    def __init__(self, context, handshake_bind, connect_bind):
        self.context = context
        self.handshake_bind = handshake_bind
        self.connect_bind = connect_bind

        self.handshake_socket = None
        self.socket = None

        self._connected = False

    def connect(self):
        # Socket to send handshake signals
        self.handshake_socket = self.context.socket(zmq.REQ)
        self.handshake_socket.connect(self.handshake_bind)
        self.handshake_socket.setsockopt(zmq.LINGER, 0)

        # Socket to actually doi pub/sub
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect(self.connect_bind)
        self.socket.setsockopt(zmq.LINGER, 0)

        poll = zmq.Poller()
        poll.register(self.handshake_socket, zmq.POLLIN)

        self.handshake_socket.send("")
        socks = dict(poll.poll(200))

        if socks.get(self.handshake_socket) == zmq.POLLIN:
            self.handshake_socket.recv()
            self.handshake_socket.close()
            self._connected = True
            return True
        else:
            self._connected = False
            self.close()
            return False

    def send(self, msg):
        if self._connected:
            self.socket.send(msg)
        elif self.connect():
            self.socket.send(msg)
        else:
            sys.stderr.write(msg)
            sys.stderr.flush()

    def close(self):
        try:
            self.handshake_socket.close()
        except ZeroMQError, err:
            pass

        try:
            self.socket.close()
        except ZeroMQError, err:
            pass

def client_factory():
    return Client(context, 'tcp://localhost:5562', 'tcp://localhost:5561')

class Pool(object):
    """
    This manages a pool of 0mq clients.

    We need 2 bindstrings - one for req/resp to do the initial
    handshaking to make sure that messages are passing through the 0mq
    connection withiout dropping packets.
    """

    def __init__(self, client_factory, size=10):
        self._clients = Queue.Queue()
        for i in range(size):
            self._clients.put(client_factory())

    def send(self, *args, **kwargs):
        with self.return_to_pool(self.socket()) as socket:
            socket.send(*args, **kwargs)

    @contextmanager
    def return_to_pool(self, sock):
        yield sock
        self._clients.put(sock)

    def socket(self):
        return self._clients.get(block=True)


def main():
    context = zmq.Context()

    client = Client(context, 'tcp://localhost:5562', 'tcp://localhost:5561')
    for i in range(1000000):
        client.send('Rhubarb');
    client.send('END')

if __name__ == '__main__':
    main()

