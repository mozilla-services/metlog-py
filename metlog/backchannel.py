# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is metlog
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****


"""
The metlog client supports a backchannel where you can modify the
state of individual loggers.

High level design:

    * each client has a backchannel that will subscribe to
      interrogation events
    * when an event arrives, the client will send responses to
      the interrogator via a second pub/sub channel.

Client Interrogation:

    * Each query comes in as a JSON blob.  The queries are only
      checked when messages are sent out via the metlog method call or 
      on a timing event.  

      Note that timing events will trigger a backchannel read if and
      only if the metlog_nosy_backchannel setting is enabled.

"""

try:
    import simplesjson as json
except ImportError:
    import json

import threading
import zmq
from base_zeromq import AbstractZmq

# We need to set the maximum number of inbound messages so that
# applications don't consume infinite memory if inbound messages are
# not processed

# Note that backchannel have shallow queues compared to the ZmqPubSender
MAX_MESSAGES = 10

class ZmqBackchannel(AbstractZmq):
    """
    Receive messages via a ZeroMQ subscriber socket.
    """

    def __init__(self, bindstr, callback_bindstr, queue_length=MAX_MESSAGES):

        # bindstr is for incoming interrogation requests into the
        # metlog client
        self.bindstr = bindstr

        # callback_bindstr is for sending responses back to listeners
        self.callback_bindstr = callback_bindstr

        self._local = threading.local()
        self._queue_length = queue_length

    @property
    def publisher(self):
        if not hasattr(self._local, 'publisher'):
            self._local.publisher = self._zmq_context.socket(zmq.PUSH)
            self._local.publisher.connect(self.callback_bindstr)
        return self._local.publisher

    @property
    def subscriber(self):
        # Socket to read from
        if not hasattr(self._local, 'subscriber'):
            self._local.subscriber = self._zmq_context.socket(zmq.SUB)
            self._local.subscriber.setsockopt(zmq.SUBSCRIBE, "")
            self._local.subscriber.connect(self.bindstr)
        return self._local.subscriber

    def send_callback(self, jdata_msg):
        self.publisher.send(json.dumps(jdata_msg))

    def recv_message(self):
        """
        Read and deserialize a message off the 0mq channel.

        If no message is there available, we just return None
        """
        try:
            msg = self.subscriber.recv(zmq.NOBLOCK)
            try:
                return json.loads(msg)
            except:
                return msg
        except zmq.ZMQError, zmq_err:
            # on read error, we don't do anything as we're in
            # non-blocking mode
            pass

