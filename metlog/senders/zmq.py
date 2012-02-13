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
import threading
try:
    import zmq
except ImportError:
    zmq = None  # NOQA


# We need to set the maximum number of outbound messages so that
# applications don't consume infinite memory if outbound messages are
# not processed
MAX_MESSAGES = 1000


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
        """
        Property that exposes zmq publisher socket. Implemented as a property
        because zmq sockets are not threadsafe and thus the actual socket
        object is stored as a threadlocal value.
        """
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

        :param msg: Dictionary representing the message.
        """
        json_msg = json.dumps(msg)
        self.publisher.send(json_msg)
