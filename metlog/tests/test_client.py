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
from datetime import datetime
from metlog.client import MetlogClient
from mock import Mock
from nose.tools import eq_, ok_
from metlog.senders.dev import DebugCaptureSender

import threading
import time
import logging

try:
    import simplejson as json
except:
    import json


class TestMetlogClient(object):
    logger = 'tests'

    def setUp(self):
        self.mock_sender = Mock()
        self.client = MetlogClient(self.mock_sender, self.logger)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.client.timer._local = threading.local()

    def tearDown(self):
        del self.mock_sender

    def _extract_full_msg(self):
        return self.mock_sender.send_message.call_args[0][0]

    def test_metlog_bare(self):
        payload = 'this is a test'
        before = datetime.utcnow().isoformat()
        msgtype = 'testtype'
        self.client.metlog(msgtype, payload=payload)
        after = datetime.utcnow().isoformat()
        full_msg = self._extract_full_msg()
        # check the payload
        eq_(full_msg['payload'], payload)
        # check the various default values
        ok_(before < full_msg['timestamp'] < after)
        eq_(full_msg['type'], msgtype)
        eq_(full_msg['severity'], self.client.severity)
        eq_(full_msg['logger'], self.logger)
        eq_(full_msg['fields'], dict())
        eq_(full_msg['env_version'], self.client.env_version)

    def test_metlog_full(self):
        metlog_args = dict(payload='this is another test',
                           timestamp=datetime.utcnow(),
                           logger='alternate',
                           severity=2,
                           fields={'foo': 'bar',
                                   'boo': 'far'})
        msgtype = 'bawlp'
        self.client.metlog(msgtype, **metlog_args)
        full_msg = self._extract_full_msg()
        metlog_args.update({'type': msgtype,
                            'env_version': self.client.env_version,
                            'timestamp': metlog_args['timestamp'].isoformat()})
        eq_(full_msg, metlog_args)

    def test_timer_contextmanager(self):
        name = 'test'
        with self.client.timer(name) as result:
            time.sleep(0.01)

        ok_(result.ms >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], str(result.ms))
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

    def test_timer_decorator(self):
        name = 'test'

        @self.client.timer(name)
        def timed():
            time.sleep(0.01)

        ok_(not self.mock_sender.send_message.called)
        timed()
        full_msg = self._extract_full_msg()
        ok_(int(full_msg['payload']) >= 10)
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

    def test_timer_with_rate(self):
        name = 'test'

        @self.client.timer(name, rate=0.01)
        def timed():
            time.sleep(0.001)

        for i in range(10):
            timed()

        # this is a weak test, but not quite sure how else to
        # test explicitly random behaviour
        ok_(self.mock_sender.send_message.call_count < 10)

    def test_incr(self):
        name = 'incr'
        self.client.incr(name)
        full_msg = self._extract_full_msg()
        eq_(full_msg['type'], 'counter')
        eq_(full_msg['logger'], self.logger)
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['payload'], '1')

        self.client.incr(name, 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], '10')


class TestDisabledTimer(object):
    logger = 'tests'

    def _extract_full_msg(self):
        return json.loads(self.mock_sender.msgs[0])

    def setUp(self):
        self.mock_sender = DebugCaptureSender()
        self.client = MetlogClient(self.mock_sender, self.logger)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.client.timer._local = threading.local()
        self.client.sender.msgs.clear()

    def test_timer_contextmanager(self):
        name = 'test'
        with self.client.timer(name) as result:
            time.sleep(0.01)

        ok_(result.ms >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], str(result.ms))
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

        # Now disable it
        self.client._disabled_timers.add('test')
        with self.client.timer('test') as result:
            time.sleep(0.01)
        assert result is None

        # Now re-enable it
        self.client._disabled_timers.remove('test')
        self.client.sender.msgs.clear()
        with self.client.timer('test') as result:
            time.sleep(0.01)

        ok_(result.ms >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], str(result.ms))
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)


    def test_timer_decorator(self):
        name = 'test'

        @self.client.timer(name)
        def foo():
            time.sleep(0.01)
        foo()

        assert len(self.client.sender.msgs) == 1
        msg = json.loads(self.client.sender.msgs[0])

        full_msg = self._extract_full_msg()
        assert int(full_msg['payload']) >= 10, "Got: %d" % int(full_msg['payload'])
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

        # Now disable it
        self.client._disabled_timers.add('test')
        self.client.sender.msgs.clear()

        @self.client.timer(name)
        def foo():
            time.sleep(0.01)
        foo()

        assert len(self.mock_sender.msgs) == 0

        # Now re-enable it
        self.client._disabled_timers.remove('test')
        self.client.sender.msgs.clear()

        @self.client.timer('test')
        def foo():
            time.sleep(0.01)
        foo()

        full_msg = self._extract_full_msg()
        assert int(full_msg['payload']) >= 10
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)


    def test_disable_all_timers(self):
        name = 'test'

        @self.client.timer(name)
        def foo():
            time.sleep(0.01)
        foo()

        assert len(self.client.sender.msgs) == 1
        msg = json.loads(self.client.sender.msgs[0])

        full_msg = self._extract_full_msg()
        assert int(full_msg['payload']) >= 10
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

        # Now disable everything
        self.client._disabled_timers.add('*')
        self.client.sender.msgs.clear()

        @self.client.timer(name)
        def foo():
            time.sleep(0.01)
        foo()

        assert len(self.mock_sender.msgs) == 0

class TestLoggingHook(object):
    logger = 'tests'

    def setUp(self):
        self.mock_sender = Mock()
        self.client = MetlogClient(self.mock_sender, self.logger)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.client.timer._local = threading.local()

    def tearDown(self):
        del self.mock_sender

    def test_logging_handler(self):
        logger = logging.getLogger('demo')
        self.client.hook_logger('demo')
        msg = "this is an info message"
        logger.info(msg)
        assert msg == self.mock_sender.send_message.call_args[0][0]['payload']

