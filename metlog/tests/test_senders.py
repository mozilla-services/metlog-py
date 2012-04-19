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
from metlog.senders import StdOutSender
from mock import patch
from nose.plugins.skip import SkipTest
from nose.tools import eq_

import json
import threading
import time


class TestZmqPubSender(object):
    logger = 'tests'

    def setUp(self):
        if zmq is None:
            raise(SkipTest)
        self.context_patcher = patch.object(ZmqPubSender, '_zmq_context')
        self.mock_zmq_context = self.context_patcher.start()
        self.sender = self._make_one()

    def tearDown(self):
        self.mock_zmq_context.stop()

    def _make_one(self):
        return ZmqPubSender(bindstrs='bindstr', pool_size=2)

    def test_publ_threadsafe(self):

        def reentrant():
            self.sender.send_message('foo')

        t0 = threading.Thread(target=reentrant)
        t1 = threading.Thread(target=reentrant)
        t0.start()
        time.sleep(0.01)  # give it time to ensure publisher is accessed
        t1.start()
        time.sleep(0.01)  # give it time to ensure publisher is accessed
        # the socket call should have happened twice, once for each thread
        mock_socket = self.mock_zmq_context.socket()
        eq_(mock_socket.connect.call_count, 2)
        eq_(mock_socket.send.call_count, 2)

    def test_send(self):
        msg = {'this': 'is',
               'a': 'test',
               'payload': 'PAYLOAD'}
        json_msg = json.dumps(msg)
        self.sender.send_message(msg)
        mock_socket = self.mock_zmq_context.socket()

        eq_(mock_socket.connect.call_count, 2)
        eq_(mock_socket.connect.call_args, (('bindstr',), {}))
        eq_(mock_socket.send.call_count, 1)

        mock_socket.send.assert_called_with(json_msg)

    def test_debug_stderr(self):
        msg = {'milk': 'shake'}
        json_msg = json.dumps(msg)
        self.sender.debug_stderr = True
        with patch('sys.stderr') as mock_stderr:
            self.sender.send_message(msg)
            eq_(mock_stderr.write.call_count, 1)
            eq_(mock_stderr.flush.call_count, 1)
            mock_stderr.write.assert_called_with(json_msg + '\n')


@patch('sys.stdout')
def test_stdout_sender(mock_stdout):
    msg = {'this': 'is',
           'a': 'test',
           'payload': 'PAYLOAD'}
    json_msg = json.dumps(msg)
    sender = StdOutSender()
    sender.send_message(msg)
    eq_(mock_stdout.write.call_count, 1)
    eq_(mock_stdout.flush.call_count, 1)
    mock_stdout.write.assert_called_with(json_msg + '\n')
