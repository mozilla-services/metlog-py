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
    import simplesjson as json
except ImportError:
    import json  # NOQA
try:
    import zmq
except ImportError:
    zmq = None  # NOQA

import Queue
import threading
import sys
import time

# We need to set the maximum number of outbound messages so that
# applications don't consume infinite memory if outbound messages are
# not processed
MAX_MESSAGES = 1000


class SimpleClient(object):
    def __init__(self, context, connect_bind, hwm=200):
        self.context = context

        self.connect_bind = connect_bind
        self.hwm = hwm
        self.socket = None

        # We need to synchronize around the connected flag
        self._connect_lock = threading.RLock()
        self._connected = False

    def connected(self):
        with self._connect_lock:
            return self._connect

    def connect(self):
        """
        Connect or re-connect a client if necessary.

        If the client is connected, return True
        """

        with self._connect_lock:
            if self._connected:
                return True
            # Socket to actually do pub/sub
            self.socket = self.context.socket(zmq.PUB)
            for bindstr in self.connect_bind:
                self.socket.connect(bindstr)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.HWM, self.hwm)
            self._connected = True

    def send(self, msg):
        self.socket.send(msg)

    def close(self):
        try:
            self.socket.close()
            with self._connect_lock:
                self._connected = False
        except zmq.ZMQError:
            pass


class HandshakingClient(object):
    def __init__(self, context, handshake_bind, connect_bind,
                 handshake_timeout=200,
                 hwm=200):

        self.context = context

        self.handshake_bind = handshake_bind
        self.connect_bind = connect_bind

        self.handshake_timeout = handshake_timeout
        self.hwm = hwm

        self.handshake_socket = None
        self.socket = None

        # We need to synchronize around the connected flag
        self._connect_lock = threading.RLock()
        self._connected = False

    def connect(self):
        """
        Connect or re-connect a client if necessary.

        If the client is connected, return True
        """
        with self._connect_lock:
            if self._connected:
                return True
            # Socket to send handshake signals
            self.handshake_socket = self.context.socket(zmq.REQ)
            self.handshake_socket.connect(self.handshake_bind)
            self.handshake_socket.setsockopt(zmq.LINGER, 0)

            # Socket to actually do pub/sub
            self.socket = self.context.socket(zmq.PUB)
            self.socket.connect(self.connect_bind)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.HWM, self.hwm)

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

    def connected(self):
        with self._connect_lock:
            return self._connected

    def send(self, msg):
        try:
            if self.connected():
                self.socket.send(msg)
            else:
                sys.stderr.write("%s\n" % msg)
                sys.stderr.flush()
        except zmq.ZMQError:
            self.close()
            sys.stderr.write("%s\n" % msg)
            sys.stderr.flush()

    def close(self):
        try:
            self.handshake_socket.close()
        except zmq.ZMQError:
            pass

        try:
            self.socket.close()
        except zmq.ZMQError:
            pass


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
        self._stop_lock = threading.RLock()
        self._stopped = False

        self._clients = Queue.Queue()

        # This list is only used to handle reconnects if the
        # connection to the 0mq subscriber dies
        self._all_clients = []

        for i in range(size):
            client = client_factory()
            self._clients.put(client)
            self._all_clients.append(client)

        def reconnect_clients():
            while True:
                for client in self._all_clients:
                    client.connect()
                if self.is_stopped():
                    break
                time.sleep(5)

        # Connect the clients on a background thread so that we can
        # startup quickly
        self._connect_thread = threading.Thread(target=reconnect_clients)
        self._connect_thread.daemon = True
        self._connect_thread.start()

    def send(self, msg):
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
        import pdb
        pdb.set_trace()
        with self._stop_lock:
            self._stopped = True
            print "Background thread stopped!"

    def is_stopped(self):
        with self._stop_lock:
            return self._stopped

    def socket(self):
        return self._clients.get()


class ZmqSender(object):
    _zmq_context = zmq.Context() if zmq is not None else None

    def send_message(self, msg):
        """
        Serialize and send a message off to the metlog listener.

        :param msg: Dictionary representing the message.
        """
        json_msg = json.dumps(msg)
        if self.debug_stderr:
            sys.stderr.write("%s\n" % json_msg)
            sys.stderr.flush()
        self.pool.send(json_msg)


class ZmqPubSender(ZmqSender):
    """
    Sends metlog messages out via a ZeroMQ publisher socket.
    """

    def __new__(cls, *args, **kwargs):
        if zmq is None:
            # no zmq -> no ZmqPubSender
            raise ValueError('Must have `pyzmq` installed to use ZmqPubSender')
        return super(ZmqPubSender, cls).__new__(cls)

    def __init__(self, bindstrs,
                 pool_size=10,
                 queue_length=MAX_MESSAGES,
                 debug_stderr=False):

        if isinstance(bindstrs, basestring):
            bindstrs = [bindstrs]

        def get_client():
            return SimpleClient(self._zmq_context,
                                bindstrs,
                                queue_length)

        self.pool = Pool(get_client, pool_size)
        self.debug_stderr = debug_stderr


class ZmqHandshakePubSender(ZmqSender):
    """
    Sends metlog messages out via a ZeroMQ publisher socket.

    Redirect all dropped messages to stderr
    """
    def __new__(cls, *args, **kwargs):
        if zmq is None:
            # no zmq -> no ZmqPubSender
            msg = 'Must have `pyzmq` installed to use ZmqHandshakePubSender'
            raise ValueError(msg)
        return super(ZmqHandshakePubSender, cls).__new__(cls)

    def __init__(self, handshake_bind, connect_bind,
            handshake_timeout, pool_size=10, hwm=200,
            debug_stderr=False):

        def get_client():
            client = HandshakingClient(self._zmq_context,
                                handshake_bind, connect_bind,
                                handshake_timeout, hwm)
            # Try to get all clients to connect right away
            client.connect()
            return client

        self.pool = Pool(get_client, pool_size)
        self.debug_stderr = debug_stderr
