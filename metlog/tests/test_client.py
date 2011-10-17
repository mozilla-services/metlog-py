from metlog.client import MetlogClient
from mock import patch
from nose.tools import eq_

import json
import threading
import time


class TestMetlogClient(object):
    def setUp(self):
        self.zmq_patcher = patch.object(MetlogClient, 'zmq_context')
        self.mock_zmq_context = self.zmq_patcher.start()
        self.client = self._make_one()

    def tearDown(self):
        self.zmq_patcher.stop()

    def _make_one(self, bindstrs=('bindstrs',)):
        return MetlogClient(bindstrs, 'tests')

    def test_publ_threadsafe(self):

        def reentrant():
            self.client.publisher

        t0 = threading.Thread(target=reentrant)
        t1 = threading.Thread(target=reentrant)
        t0.start()
        time.sleep(0.01)  # give it time to ensure publisher is accessed
        t1.start()
        time.sleep(0.01)  # give it time to ensure publisher is accessed
        # the socket call should have happened twice, once for each thread
        eq_(self.mock_zmq_context.socket.call_count, 2)

    def test_send(self):
        msg = {'this': 'is',
               'a': 'test'}
        json_msg = json.dumps(msg)
        self.client._send_message(msg)
        publisher = self.client.publisher
        publisher.bind.assert_called_once_with('bindstrs')
        publisher.send.assert_called_once_with(json_msg)
        publisher.bind.reset_mock()
        publisher.send.reset_mock()

    def test_metlog(self):
        msg = 'this is a test'
        self.client.metlog(payload=msg)
        self.client.publisher.send.reset_mock()
