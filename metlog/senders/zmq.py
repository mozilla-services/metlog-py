# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from __future__ import absolute_import
try:
    import simplejson as json
except ImportError:
    import json  # NOQA

import threading
import sys
import time

if 'gevent.monkey' in sys.modules:
    from gevent import queue as Queue
else:
    import Queue  # NOQA

try:
    if 'gevent.monkey' in sys.modules:
        from gevent_zeromq import zmq
    else:
        import zmq  # NOQA
except ImportError:
    zmq = None  # NOQA


# We need to set the maximum number of outbound messages so that
# applications don't consume infinite memory if outbound messages are
# not processed
MAX_MESSAGES = 1000


class BaseClient(object):
    def __init__(self, context):
        self.context = context

        # We need to synchronize around the connected flag
        self._connect_lock = threading.RLock()
        self.set_connected(False)

    def set_connected(self, state):
        with self._connect_lock:
            self._connected = state
        return self.connected()

    def connected(self):
        with self._connect_lock:
            return self._connected


class SimpleClient(BaseClient):
    def __init__(self, context, connect_bind, hwm=200):
        super(SimpleClient, self).__init__(context)

        self.connect_bind = connect_bind
        self.hwm = hwm
        self.socket = None

        # The pub socket must be created
        # Socket to actually do pub/sub
        self.socket = self.context.socket(zmq.PUB)
        for bindstr in self.connect_bind:
            self.socket.connect(bindstr)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.HWM, self.hwm)
        self.set_connected(True)

    def connect(self):
        """
        For the SimpleClient, connect() does nothing as the connect is
        handled in the initializer
        """
        return True

    def send(self, msg):
        self.socket.send(msg)


class HandshakingClient(BaseClient):
    def __init__(self, context, handshake_bind, connect_bind,
                 handshake_timeout=200,
                 hwm=200):
        super(HandshakingClient, self).__init__(context)

        self.handshake_bind = handshake_bind
        self.connect_bind = connect_bind

        self.handshake_timeout = handshake_timeout
        self.hwm = hwm

        self.handshake_socket = None
        self.socket = None

        # Socket to actually do pub/sub
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect(self.connect_bind)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.HWM, self.hwm)

    def connect(self):
        """
        Connect To the 0mq REPL socket and attempt a handshake to
        ensure we're properly connected.
        """
        # Socket to send handshake signals
        self.handshake_socket = None
        try:
            self.handshake_socket = self.context.socket(zmq.REQ)
            self.handshake_socket.connect(self.handshake_bind)
            self.handshake_socket.setsockopt(zmq.LINGER, 0)

            poll = zmq.Poller()
            poll.register(self.handshake_socket, zmq.POLLIN)

            self.handshake_socket.send("")
            socks = dict(poll.poll(self.handshake_timeout))

            if socks.get(self.handshake_socket) == zmq.POLLIN:
                self.handshake_socket.recv()
                return self.set_connected(True)
            else:
                return self.set_connected(False)
        finally:
            # Shutdown the handshake
            if self.handshake_socket != None:
                self.handshake_socket.close()

    def send(self, msg):
        try:
            if self.connected():
                self.socket.send(msg)
            else:
                sys.stderr.write("%s\n" % msg)
                sys.stderr.flush()
        except zmq.ZMQError:
            sys.stderr.write("%s\n" % msg)
            sys.stderr.flush()


class Pool(object):
    """
    This is a threadsafe pool of 0mq clients.

    :param client_factory:
        a factory function that creates Client instances
    :param size:
        The number of clients to create in the pool
    :param livecheck:
        The time in seconds to wait to ping the server
        from each client
    """

    def __init__(self, client_factory, size=10, livecheck=10):
        self._stop_lock = threading.RLock()
        self._stopped = False

        self._clients = Queue.Queue()
        self._livecheck = livecheck

        # This list is only used to handle reconnects if the
        # connection to the 0mq subscriber dies
        self._all_clients = []

        for i in range(size):
            client = client_factory()
            self._clients.put(client)
            self._all_clients.append(client)

        # Connect the clients on a background thread so that we can
        # startup quickly
        self._connect_thread_started = False

        def background_thread():
            while True:
                for client in self._all_clients:
                    client.connect()
                if self.is_stopped():
                    break
                time.sleep(self._livecheck)

        self._connect_thread = threading.Thread(target=background_thread)
        self._connect_thread.daemon = True

        self.start_reconnecting()

    def start_reconnecting(self):
        """
        Start the background thread that handles pings to the server
        to synchronize the initial pub/sub
        """
        with self._stop_lock:
            if self._connect_thread_started:
                return
            self._connect_thread_started = True

        self._connect_thread.start()

    def send(self, msg):
        """
        Threadsafely send a single text message over a 0mq socket
        """
        sock = None
        try:
            sock = self.socket()
            sock.send(msg)
        except Queue.Empty:
            # Sometimes, we'll get nothing
            sys.stderr.write("%s\n" % msg)
        finally:
            if sock:
                self._clients.put(sock)

    def stop(self):
        """
        Shutdown the background reconnection thread
        """
        with self._stop_lock:
            self._stopped = True

    def is_stopped(self):
        with self._stop_lock:
            return self._stopped

    def socket(self):
        return self._clients.get()


class ZmqSender(object):
    """
    Base class for ZmqPubSender and ZmqHandshakePubSender
    """

    _zmq_context = zmq.Context() if zmq is not None else None

    def __new__(cls, *args, **kwargs):
        """
        Just check that we have pyzmq installed
        """
        if zmq is None:
            # no zmq -> no ZmqPubSender
            raise ValueError('Must have `pyzmq` installed to use ZmqPubSender')
        return super(ZmqSender, cls).__new__(cls)

    def send_message(self, msg):
        """
        Serialize and send a message off to the metlog listener.

        :param msg: Dictionary representing the message.
        """
        json_msg = json.dumps(msg)
        if self.debug_stderr:
            sys.stderr.write(json_msg + '\n')
            sys.stderr.flush()
        self.pool.send(json_msg)


class ZmqPubSender(ZmqSender):
    """
    Sends metlog messages out via a ZeroMQ publisher socket.
    """

    def __init__(self, bindstrs,
                 pool_size=10,
                 queue_length=MAX_MESSAGES,
                 livecheck=10,
                 debug_stderr=False):
        """
        :param bindstrs:
            One or more URL strings which 0mq recognizes as an
            endpoint URL. Either a string or a list of strings is
            accepted.
        :param pool_size:
            The number of connections we maintain to the 0mq backend
        :param livecheck:
            Polling interval in seconds between client.connect() calls
        :param debug_stderr:
            Boolean flag to send messages to stderr in addition to the
            actual 0mq socket
        """

        if isinstance(bindstrs, basestring):
            bindstrs = [bindstrs]

        def get_client():
            return SimpleClient(self._zmq_context,
                                bindstrs,
                                queue_length)

        self.pool = Pool(client_factory=get_client,
                size=pool_size,
                livecheck=livecheck)
        self.debug_stderr = debug_stderr


class ZmqHandshakePubSender(ZmqSender):
    """
    Sends metlog messages out via a ZeroMQ publisher socket.

    Redirect all dropped messages to stderr
    """

    def __init__(self, handshake_bind, connect_bind,
            handshake_timeout, pool_size=10, hwm=200,
            livecheck=10,
            debug_stderr=False):
        """
        :param handshake_bind:
            A single 0mq recognized endpoint URL.
            This should point to the endpoint for handshaking of
            connections
        :param connect_bind:
            A single 0mq recognized endpoint URL.
            This should point ot the endpoint for sending actual
            Metlog messages.
        :param handshake_timeout:
            Timeout in ms to wait for responses from the 0mq server on
            handshake
        :param pool_size:
            The number of connections we maintain to the 0mq backend
        :param hwm:
            High water mark. Set the maximum number of messages to
            queue before dropping messages in case of a slow reading
            0mq server.
        :param livecheck:
            Polling interval in seconds between client.connect() calls
        :param debug_stderr:
            Boolean flag to send messages to stderr in addition to the
            actual 0mq socket
        """

        def get_client():
            client = HandshakingClient(self._zmq_context,
                                handshake_bind, connect_bind,
                                handshake_timeout, hwm)
            # Try to get all clients to connect right away
            client.connect()
            return client

        self.pool = Pool(client_factory=get_client,
                size=pool_size,
                livecheck=livecheck)
        self.debug_stderr = debug_stderr
