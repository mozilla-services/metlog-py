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
import sys

# We need to set the maximum number of outbound messages so that
# applications don't consume infinite memory if outbound messages are
# not processed
MAX_MESSAGES = 1000


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

    def send(self, msg):
        try:
            if self._connected:
                self.socket.send(msg)
            elif self.connect():
                self.socket.send(msg)
            else:
                sys.stderr.write(msg)
                sys.stderr.flush()
        except zmq.ZMQError:
            self.close()
            sys.stderr.write(msg)
            sys.stderr.flush()

    def close(self):
        try:
            self.handshake_socket.close()
        except ZMQError, err:
            pass

        try:
            self.socket.close()
        except ZMQError, err:
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


class ZmqPubSender(object):
    """
    Sends metlog messages out via a ZeroMQ publisher socket.
    """

    _zmq_context = zmq.Context() if zmq is not None else None

    def __new__(cls, *args, **kwargs):
        if zmq is None:
            # no zmq -> no ZmqPubSender
            raise ValueError('Must have `pyzmq` installed to use ZmqPubSender')
        return super(ZmqPubSender, cls).__new__(cls)

    def __init__(self, handshake_bind,
                 connect_bind,
                 handshake_timeout,
                 pool_size=10,
                 queue_length=MAX_MESSAGES):

        def get_client():
            return HandshakingClient(_zmq_context,
                                     handshake_bind,
                                     connect_bind,
                                     handshake_timeout,
                                     queue_length)

        self.pool = Pool(get_client, pool_size)

    def send_message(self, msg):
        """
        Serialize and send a message off to the metlog listener.

        :param msg: Dictionary representing the message.
        """
        json_msg = json.dumps(msg)
        self.pool.send(json_msg)
