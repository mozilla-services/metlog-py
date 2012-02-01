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
from metlog.senders import ZmqPubSender, zmq
from mock import patch
from nose.plugins.skip import SkipTest
from nose.tools import eq_

import json
import threading
import time


@patch.object(ZmqPubSender, '_zmq_context')
class TestZmqPubSender(object):
    logger = 'tests'

    def setUp(self):
        if zmq is None:
            raise(SkipTest)
        self.sender = self._make_one()

    def _make_one(self):
        return ZmqPubSender(bindstrs='bindstr')

    def test_publ_threadsafe(self, mock_zmq_context):

        def reentrant():
            self.sender.publisher

        t0 = threading.Thread(target=reentrant)
        t1 = threading.Thread(target=reentrant)
        t0.start()
        time.sleep(0.01)  # give it time to ensure publisher is accessed
        t1.start()
        time.sleep(0.01)  # give it time to ensure publisher is accessed
        # the socket call should have happened twice, once for each thread
        eq_(mock_zmq_context.socket.call_count, 2)

    def test_send(self, mock_zmq_context):
        msg = {'this': 'is',
               'a': 'test',
               'payload': 'PAYLOAD'}
        json_msg = json.dumps(msg)
        self.sender.send_message(msg)
        publisher = self.sender.publisher
        publisher.connect.assert_called_with('bindstr')
        publisher.send.assert_called_with(json_msg)
