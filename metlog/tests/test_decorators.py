# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import unittest
from metlog.client import MetlogClient
from metlog.helper import HELPER
from metlog.exceptions import MethodNotFoundError
from metlog.config import Config
from metlog.decorators import apache_log
from metlog.decorators import incr_count
from metlog.decorators import timeit
from metlog.decorators import get_tlocal
from metlog.decorators.util import rebind_dispatcher
from webob.request import Request

try:
    import simplejson as json
except:
    import json   # NOQA

class TestCannedDecorators(unittest.TestCase):
    def setUp(self):
        config = Config("""
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
        msgs = [json.loads(m) for m in HELPER._client.sender.msgs]
        assert len(msgs) == 2

        for msg in msgs:
            expected = 'metlog.tests.test_decorators:ordering_1'
            actual = msg['fields']['name']
            assert actual == expected

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
        msgs = [json.loads(m) for m in HELPER._client.sender.msgs]
        assert len(msgs) == 2

        for msg in msgs:
            expected = 'metlog.tests.test_decorators:ordering_2'
            actual = msg['fields']['name']
            assert actual == expected

        # Ordering of log messages should occur in the in->out
        # ordering of decoration
        assert msgs[0]['type'] == 'counter'
        assert msgs[1]['type'] == 'timer'

    def test_reset_helper(self):
        assert isinstance(HELPER._client, MetlogClient)
        HELPER.set_client(None)
        assert HELPER._client == None

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
        msg = json.loads(HELPER._client.sender.msgs[0])
        assert 'foo' in msg['fields']['threadlocal']
        assert msg['fields']['threadlocal']['foo'] == 'bar'


class TestDisabledMetrics(unittest.TestCase):
    def setUp(self):
        config = Config("""
        [test1]
        enabled=false
        sender_backend = metlog.senders.DebugCaptureSender
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
            raise exceptions.AssertionError(\
                    'Class definition should have failed.')
        except MethodNotFoundError, mnfe:
            assert mnfe.args[0].startswith("No such method")


def test_decorators_with_args():
    # TODO: implement some tests that verify that @timeit and @incr_count will
    # accept standard metlog arguments
    raise NotImplementedError

