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
try:
    import simplesjson as json
except ImportError:
    import json
import sys
import threading
import zmq


# We need to set the maximum number of outbound messages so that
# applications don't consume infinite memory if outbound messages are
# not processed
MAX_MESSAGES = 1000


class ZmqPubSender(object):
    """
    Sends metlog messages out via a ZeroMQ publisher socket.
    """

    _zmq_context = zmq.Context()

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
