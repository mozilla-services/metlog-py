# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****


try:
    import simplesjson as json
except ImportError:
    import json  # NOQA
import sys
import threading
try:
    import zmq
except ImportError:
    zmq = None


# We need to set the maximum number of outbound messages so that
# applications don't consume infinite memory if outbound messages are
# not processed
MAX_MESSAGES = 1000


class ZmqPubSender(object):
    """
    Sends metlog messages out via a ZeroMQ publisher socket.
    """

    _zmq_context = zmq.Context() if zmq is not None else None

    def __new__(cls, **kwargs):
        if zmq is None:
            # no zmq -> no ZmqPubSender
            raise ValueError('Must have `pyzmq` installed to use ZmqPubSender')
        return super(ZmqPubSender, cls).__new__(cls)

    def __init__(self, bindstrs, queue_length=MAX_MESSAGES):
        if isinstance(bindstrs, basestring):
            bindstrs = [bindstrs]
        self.bindstrs = bindstrs
        self._queue_length = queue_length

        # The threadlocal is on the *instance* instead of the class so
        # that we can create multiple instances of the ZmqPubSender
        # that target dfferent bindstrings
        self._local = threading.local()

    @property
    def publisher(self):
        if not hasattr(self._local, 'publisher'):
            # 0mq sockets aren't threadsafe, so bind them into a
            # threadlocal
            self._local.publisher = self._zmq_context.socket(zmq.PUB)
            self._local.publisher.setsockopt(zmq.HWM, self._queue_length)

            for bindstr in self.bindstrs:
                self._local.publisher.connect(bindstr)
        return self._local.publisher

    def send_message(self, msg):
        """
        Serialize and send a message off to the metlog listener.

        :param msg: Dictionary representing the message.  The 'payload' value
        will be JSONified and turned into the 0mq message payload, the
        remaining key-value pairs will be JSONified and sent as the message
        envelope.
        """
        json_msg = json.dumps(msg)
        self.publisher.send(json_msg)


class StdOutSender(object):
    """
    Emits metlog messages to stdout for dev purposes.
    """
    def send_message(self, msg):
        json_msg = json.dumps(msg)
        sys.stdout.write('%s\n' % json_msg)
        sys.stdout.flush()


class DebugCaptureSender(object):
    """
    Capture upto 100 metlog messages in a circular buffer for
    inspection later

    This is only for DEBUGGING.  Do not use this for anything except
    development.

    Note that we're storing the raw message and only using JSON
    serialization as a weak error checking facility to make sure
    messages are serializable
    """
    def __init__(self, **kwargs):
        self._kwargs = kwargs
        import collections
        self.msgs = collections.deque(maxlen=100)

    def send_message(self, msg):
        json.dumps(msg)
        self.msgs.append(msg)
