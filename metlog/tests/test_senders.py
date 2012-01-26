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
