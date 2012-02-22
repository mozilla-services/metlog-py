# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

from metlog import logger
from metlog.client import MetlogClient
from metlog.client import SEVERITY
from metlog.config import Config
from metlog.decorators import apache_log
from metlog.decorators import get_tlocal
from metlog.decorators import incr_count
from metlog.decorators import timeit
from metlog.decorators.util import rebind_dispatcher
from metlog.exceptions import MethodNotFoundError
from metlog.helper import HELPER
from metlog.senders import DebugCaptureSender
from webob.request import Request
import unittest

class TestHelperSetup(unittest.TestCase):
    """
    The metlog helper system has been changed so that the
    """
    def setUp(self):
        config = Config("""\
        [test1]
        enabled=false
        """, 'test1')
        HELPER.configure(config)

    def test_helper(self):


        config = Config("""\
        [test1]
        enabled=true
        sender_backend=metlog.senders.DebugCaptureSender
        """, 'test1')

        # Make sure we have no client setup yet
        assert HELPER._client is None

        HELPER.configure(config)
        assert HELPER._client != None
        assert isinstance(HELPER._client.sender, DebugCaptureSender)

    def test_reset_helper(self):
        config = Config("""\
        [test1]
        enabled=true
        sender_backend=metlog.senders.DebugCaptureSender
        """, 'test1')
        HELPER.configure(config)
        assert isinstance(HELPER._client, MetlogClient)

        HELPER.set_client(None)
        assert HELPER._client == None


class TestCannedDecorators(unittest.TestCase):
    def setUp(self):
        config = Config("""\
        [test1]
        enabled=true
        sender_backend=metlog.senders.DebugCaptureSender
        """, 'test1')

        HELPER.configure(config)

    def test_decorator_ordering(self):
        '''
        decorator ordering may matter when Ops goes to look at the
        logs. Make sure we capture stuff in the right order
        '''
        HELPER._client.sender.msgs.clear()
        assert len(HELPER._client.sender.msgs) == 0

        @incr_count
        @timeit
        def ordering_1(x, y):
            return x + y

        ordering_1(5, 6)
        msgs = HELPER._client.sender.msgs
        assert len(msgs) == 2

        for msg in msgs:
            expected = 'metlog.tests.test_decorators:ordering_1'
            actual = msg['fields']['name']
            assert actual == expected, "Got: %s" % actual

        # First msg should be counter, then timer as decorators are
        # applied inside to out, but execution is outside -> in
        assert msgs[0]['type'] == 'timer'
        assert msgs[1]['type'] == 'counter'

        HELPER._client.sender.msgs.clear()
        assert len(HELPER._client.sender.msgs) == 0

        @timeit
        @incr_count
        def ordering_2(x, y):
            return x + y

        ordering_2(5, 6)
        msgs = HELPER._client.sender.msgs
        assert len(msgs) == 2

        for msg in msgs:
            expected = 'metlog.tests.test_decorators:ordering_2'
            actual = msg['fields']['name']
            assert actual == expected

        # Ordering of log messages should occur in the in->out
        # ordering of decoration
        assert msgs[0]['type'] == 'counter'
        assert msgs[1]['type'] == 'timer'

    def test_apache_logger(self):
        HELPER._client.sender.msgs.clear()
        msgs = HELPER._client.sender.msgs
        assert len(msgs) == 0

        @apache_log
        def some_method(request):
            data = get_tlocal()
            data['foo'] = 'bar'

        req = Request({'PATH_INFO': '/foo/bar',
                       'SERVER_NAME': 'somehost.com',
                       'SERVER_PORT': 80,
                       })
        some_method(req)
        msg = HELPER._client.sender.msgs
        msg = msgs[0]
        assert 'foo' in msg['fields']['threadlocal']
        assert msg['fields']['threadlocal']['foo'] == 'bar'


class TestDisabledMetrics(unittest.TestCase):
    def setUp(self):
        config = Config("""
        [test1]
        enabled=false
        """, 'test1')
        HELPER.configure(config)
        assert HELPER._client == None

    def test_no_rebind(self):
        # Test that rebinding of methods doesn't occur if metlog is
        # completely disabled
        class SomeClass(object):
            @rebind_dispatcher('rebind_method')
            def mymethod(self, x, y):
                return x * y

            def rebind_method(self, x, y):
                return x - y

        obj = SomeClass()
        assert obj.mymethod(5, 6) == 30


class TestRebindMethods(unittest.TestCase):
    def setUp(self):
        config = Config("""
        [test1]
        enabled=true
        sender_backend=metlog.senders.DebugCaptureSender
        """, 'test1')
        HELPER.configure(config)

    def test_bad_rebind(self):
        try:
            class BarClass(object):
                @rebind_dispatcher('bad_rebind')
                def mymethod(self, x, y):
                    return x * y

                def foo(self, x, y):
                    pass

            foo = BarClass()
            foo.mymethod(5, 6)
            raise AssertionError(\
                    'Class definition should have failed.')
        except MethodNotFoundError, mnfe:
            assert mnfe.args[0].startswith("No such method")


class TestSimpleLogger(unittest.TestCase):
    def setUp(self):
        config = Config("""
        [test1]
        enabled=true
        sender_backend=metlog.senders.DebugCaptureSender
        """, 'test1')
        HELPER.configure(config)

    def test_oldstyle_logger(self):
        msgs = [(SEVERITY.DEBUG, 'debug', logger.debug),
        (SEVERITY.INFORMATIONAL, 'info', logger.info),
        (SEVERITY.WARNING, 'warn', logger.warn),
        (SEVERITY.ERROR, 'error', logger.error),
        (SEVERITY.ALERT, 'exception', logger.exception),
        (SEVERITY.CRITICAL, 'critical', logger.critical)]

        for lvl, msg, method in msgs:
            method("some %s" % msg)
            msgs = HELPER._client.sender.msgs

            assert len(msgs) == 1
            timer_call = msgs[0]
            assert timer_call['logger'] == 'anonymous'
            assert timer_call['type'] == 'oldstyle'
            assert timer_call['payload'] == 'some %s' % msg
            assert timer_call['severity'] == lvl

            HELPER._client.sender.msgs.clear()
