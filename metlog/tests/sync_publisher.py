#
# Synchronized publisher. This is like a metlog cliennt
#
import zmq
import Queue
import sys
from contextlib import contextmanager
import threading
import time

class Client(object):
    def __init__(self, context, handshake_bind, connect_bind,
            handshake_timeout=200):

        self.context = context

        self.handshake_bind = handshake_bind
        self.connect_bind = connect_bind

        self.handshake_timeout = handshake_timeout

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
        socks = dict(poll.poll(self.handshake_timeout))

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

def client_factory(context):
    def get_client():
        return Client(context, 'tcp://localhost:5562', 'tcp://localhost:5561')
    return get_client

class Pool(object):
    """
    This is a threadsafe poool of 0mq clients.

    :param client_factory:
        a factory function which takes no arguments and will generate
        client instances. Clients are responsible to rebind themselves
        if necessary
    :param size: The number of clients to create in the pool
    """

    def __init__(self, client_factory, size=10):
        self._clients = Queue.Queue()
        for i in range(size):
            self._clients.put(client_factory())

    def send(self, msg):
        sock = None
        try:
            sock = self.socket()
            sock.send(msg)
        except Queue.Empty:
            # Sometimes, we'll get nothing
            sys.stderr.write(msg)
        finally:
            if sock:
                self._clients.put(sock)

    def socket(self):
        return self._clients.get()

def main():
    context = zmq.Context()

    pool = Pool(client_factory(context))

    def threaded_send():
        for i in range(10000):
            pool.send('Rhubarb');

    for i in range(10):
        t = threading.Thread(target=threaded_send)
        t.daemon = True
        t.start()

    time.sleep(10)
    pool.send('END')

if __name__ == '__main__':
    main()

