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
#   Victor Ng (vng@mozilla.com)
# ***** END LICENSE BLOCK *****
from __future__ import absolute_import

import sys

if 'gevent.monkey' in sys.modules:
    from gevent import queue as Queue
    from gevent import monkey
    monkey.patch_all()
else:
    import Queue  # NOQA

try:
    if 'gevent.monkey' in sys.modules:
        from gevent_zeromq import zmq
    else:
        import zmq  # NOQA
except ImportError:
    zmq = None  # NOQA

from metlog.senders.async_push.source import AsyncSender
from metlog.senders.lazypirate.client import LazyPirateClient

try:
    import simplejson as json
except ImportError:
    import json  # NOQA

# We need to set the maximum number of outbound messages so that
# applications don't consume infinite memory if outbound messages are
# not processed
MAX_MESSAGES = 1000


class HandshakingClient(object):
    """
    TODO: this class doesn't really do anything - get rid of it
    and just use the AsyncSender directly
    """
    def __init__(self, context, handshake_bind, connect_bind,
            hwm=200):

        self.queue = Queue.Queue(500)
        self.context = context
        self.handshake_bind = handshake_bind
        self.connect_bind = connect_bind

        self.hwm = hwm

        self.handshake_socket = None
        self.socket = None

        # Socket to actually do PUSH
        # We need to run the sender as its own thread since the
        # heartbeat must run as it's own thread.  When the heartbeat
        # dies - *some* thread of control must close the sockets.
        # The main thread can't do it since we don't have coroutines
        # everywhere and there's now way to tell the main thread to go
        # stop each of the 0mq sockets
        self.async_sender = AsyncSender(self.context, self.queue,
                self.connect_bind, self.hwm)

        # Fire up the thread
        self.async_sender.start()

    def reconnect_sockets(self):
        self.async_sender.reconnect = True

    def send(self, msg):
        self.queue.put(msg)


class Pool(object):
    """
    This is a threadsafe pool of 0mq clients.

    :param client_factory:
        a factory function that creates Client instances
    :param size:
        The number of clients to create in the pool
    """

    def __init__(self, context, client_factory, handshake_bind, size=10):
        self._clients = Queue.Queue()

        self.context = context
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

        self.lazy_pirate = LazyPirateClient(self.context,
                self.shutdown_hook, handshake_bind)
        self.lazy_pirate.start()

    def shutdown_hook(self):
        for client in self._all_clients:
            client.reconnect_sockets()

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

        :param msg: Dictionary representing the message
        """
        json_msg = json.dumps(msg)
        if self.debug_stderr:
            sys.stderr.write(json_msg + '\n')
            sys.stderr.flush()
        self.pool.send(json_msg)


class ZmqHandshakePubSender(ZmqSender):
    """
    Sends metlog messages out via a ZeroMQ publisher socket.

    Redirect all dropped messages to stderr
    """

    def __init__(self, handshake_bind, connect_bind,
            handshake_timeout, pool_size=10, hwm=200,
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
        :param debug_stderr:
            Boolean flag to send messages to stderr in addition to the
            actual 0mq socket
        """

        def get_client():
            client = HandshakingClient(self._zmq_context,
                                handshake_bind, connect_bind,
                                hwm)
            # Try to get all clients to connect right away
            return client

        self.pool = Pool(context=self._zmq_context,
                client_factory=get_client,
                handshake_bind=handshake_bind,
                size=pool_size)
        self.debug_stderr = debug_stderr
