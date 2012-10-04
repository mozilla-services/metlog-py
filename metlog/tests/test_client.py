# -*- coding: utf-8 -*-

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
from datetime import datetime
from metlog.client import MetlogClient, SEVERITY
from mock import Mock
from nose.tools import eq_, ok_
from metlog.senders.dev import DebugCaptureSender

import StringIO
import os
import socket
import sys
import threading
import time

try:
    import simplejson as json
except:
    import json  # NOQA


class TestMetlogClient(object):
    logger = 'tests'
    timer_name = 'test'

    def setUp(self):
        self.mock_sender = Mock()
        self.client = MetlogClient(self.mock_sender, self.logger)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.timer_ob = self.client.timer(self.timer_name)
        self.timer_ob.__dict__['_local'] = threading.local()

    def tearDown(self):
        del self.timer_ob.__dict__['_local']
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
        eq_(full_msg['metlog_pid'], os.getpid())
        eq_(full_msg['metlog_hostname'], socket.gethostname())
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
        actual_msg = self._extract_full_msg()
        metlog_args.update({'type': msgtype,
                            'env_version': self.client.env_version,
                            'metlog_pid': os.getpid(),
                            'metlog_hostname': socket.gethostname(),
                            'timestamp': metlog_args['timestamp'].isoformat()})
        eq_(actual_msg, metlog_args)

    def test_oldstyle(self):
        payload = 'debug message'
        self.client.debug(payload)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], payload)
        eq_(full_msg['severity'], SEVERITY.DEBUG)

    def test_oldstyle_args(self):
        payload = '1, 2: %s\n3, 4: %s'
        args = ('buckle my shoe', 'shut the door')
        self.client.warn(payload, *args)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], payload % args)

    def test_oldstyle_mapping_arg(self):
        payload = '1, 2: %(onetwo)s\n3, 4: %(threefour)s'
        args = {'onetwo': 'buckle my shoe',
                'threefour': 'shut the door'}
        self.client.warn(payload, args)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], payload % args)

    def test_oldstyle_exc_info(self):
        payload = 'traceback ahead -->'
        try:
            a = b  # NOQA
        except NameError:
            self.client.error(payload, exc_info=True)
        full_msg = self._extract_full_msg()
        ok_(full_msg['payload'].startswith(payload))
        ok_("NameError: global name 'b' is not defined" in full_msg['payload'])
        ok_('test_client.py' in full_msg['payload'])

    def test_oldstyle_exc_info_auto(self):
        payload = 'traceback ahead -->'
        try:
            a = b  # NOQA
        except NameError:
            self.client.exception(payload)
        full_msg = self._extract_full_msg()
        ok_(full_msg['payload'].startswith(payload))
        ok_("NameError: global name 'b' is not defined" in full_msg['payload'])
        ok_('test_client.py' in full_msg['payload'])

    def test_oldstyle_exc_info_passed(self):
        def name_error():
            try:
                a = b  # NOQA
            except NameError:
                return sys.exc_info()

        ei = name_error()
        payload = 'traceback ahead -->'
        self.client.critical(payload, exc_info=ei)
        full_msg = self._extract_full_msg()
        ok_(full_msg['payload'].startswith(payload))
        ok_("NameError: global name 'b' is not defined" in full_msg['payload'])
        ok_('test_client.py' in full_msg['payload'])

    def test_timer_contextmanager(self):
        name = self.timer_name
        with self.client.timer(name) as timer:
            time.sleep(0.01)

        ok_(timer.result >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], str(timer.result))
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

    def test_timer_decorator(self):
        @self.client.timer(self.timer_name)
        def timed():
            time.sleep(0.01)

        ok_(not self.mock_sender.send_message.called)
        timed()
        full_msg = self._extract_full_msg()
        ok_(int(full_msg['payload']) >= 10)
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], self.timer_name)
        eq_(full_msg['fields']['rate'], 1)

    def test_timer_with_rate(self):
        name = self.timer_name

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
        # You have to have a rate set here
        eq_(full_msg['fields']['rate'], 1)
        eq_(full_msg['payload'], '1')

        self.client.incr(name, 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], '10')


class TestDisabledTimer(object):
    logger = 'tests'
    timer_name = 'test'

    def _extract_full_msg(self):
        return json.loads(self.mock_sender.msgs[0])

    def setUp(self):
        self.mock_sender = DebugCaptureSender()
        self.client = MetlogClient(self.mock_sender, self.logger)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.timer_ob = self.client.timer(self.timer_name)
        self.timer_ob.__dict__['_local'] = threading.local()

    def tearDown(self):
        self.client.sender.msgs.clear()
        del self.timer_ob.__dict__['_local']

    def test_timer_contextmanager(self):
        name = self.timer_name
        with self.client.timer(name) as timer:
            time.sleep(0.01)

        ok_(timer.result >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], str(timer.result))
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

        # Now disable it
        self.client._disabled_timers.add(name)
        with self.client.timer(name) as timer:
            time.sleep(0.01)
            ok_(timer.result is None)

        # Now re-enable it
        self.client._disabled_timers.remove(name)
        self.client.sender.msgs.clear()
        with self.client.timer(name) as timer:
            time.sleep(0.01)

        ok_(timer.result >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], str(timer.result))
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

    def test_timer_decorator(self):
        name = self.timer_name

        @self.client.timer(name)
        def foo():
            time.sleep(0.01)
        foo()

        eq_(len(self.client.sender.msgs), 1)

        full_msg = self._extract_full_msg()
        ok_(int(full_msg['payload']) >= 10,
            "Got: %d" % int(full_msg['payload']))
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

        # Now disable it
        self.client._disabled_timers.add(name)
        self.client.sender.msgs.clear()

        @self.client.timer(name)
        def foo2():
            time.sleep(0.01)
        foo2()

        eq_(len(self.mock_sender.msgs), 0)

        # Now re-enable it
        self.client._disabled_timers.remove(name)
        self.client.sender.msgs.clear()

        @self.client.timer(name)
        def foo3():
            time.sleep(0.01)
        foo3()

        full_msg = self._extract_full_msg()
        ok_(int(full_msg['payload']) >= 10)
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

    def test_disable_all_timers(self):
        name = self.timer_name

        @self.client.timer(name)
        def foo():
            time.sleep(0.01)
        foo()

        eq_(len(self.client.sender.msgs), 1)

        full_msg = self._extract_full_msg()
        ok_(int(full_msg['payload']) >= 10)
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

        # Now disable everything
        self.client._disabled_timers.add('*')
        self.client.sender.msgs.clear()

        @self.client.timer(name)
        def foo2():
            time.sleep(0.01)
        foo2()

        eq_(len(self.mock_sender.msgs), 0)


class TestUnicode(object):
    logger = 'tests'
    timer_name = 'test'

    def setUp(self):
        self.mock_sender = Mock()
        self.mock_sender.send_message.side_effect = \
                UnicodeError("UnicodeError encoding user data")
        self.client = MetlogClient(self.mock_sender, self.logger)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.timer_ob = self.client.timer(self.timer_name)
        self.timer_ob.__dict__['_local'] = threading.local()

        self.old_stderr = sys.stderr
        sys.stderr = StringIO.StringIO()

    def tearDown(self):
        del self.timer_ob.__dict__['_local']
        del self.mock_sender
        sys.stderr = self.old_stderr

    def test_unicode_failure(self):
        msg = "mock will raise unicode error here"
        self.client.send_message(msg)
        sys.stderr.seek(0)
        err = sys.stderr.read()
        ok_('Error sending' in err)
