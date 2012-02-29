# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import unittest
from metlog.config import client_from_text_config
from metlog.client import MetlogClient
from metlog.decorators.base import CLIENT_WRAPPER
from metlog.exceptions import MethodNotFoundError
from metlog.decorators import incr_count
from metlog.decorators import timeit
from metlog.decorators.base import rebind_dispatcher

try:
    import simplejson as json
except:
    import json   # NOQA


class TestCannedDecorators(unittest.TestCase):
    def setUp(self):
        client = client_from_text_config("""
        [test1]
        enabled=true
        sender_class=metlog.senders.DebugCaptureSender
        """, 'test1')
        CLIENT_WRAPPER.client = client

    def test_decorator_ordering(self):
        '''
        decorator ordering may matter when Ops goes to look at the
        logs. Make sure we capture stuff in the right order
        '''
        CLIENT_WRAPPER.client.sender.msgs.clear()
        assert len(CLIENT_WRAPPER.client.sender.msgs) == 0

        @incr_count
        @timeit
        def ordering_1(x, y):
            return x + y

        ordering_1(5, 6)
        msgs = [json.loads(m) for m in CLIENT_WRAPPER.client.sender.msgs]
        assert len(msgs) == 2

        for msg in msgs:
            expected = 'metlog.tests.test_decorators:ordering_1'
            actual = msg['fields']['name']
            assert actual == expected

        # First msg should be counter, then timer as decorators are
        # applied inside to out, but execution is outside -> in
        assert msgs[0]['type'] == 'timer'
        assert msgs[1]['type'] == 'counter'

        CLIENT_WRAPPER.client.sender.msgs.clear()
        assert len(CLIENT_WRAPPER.client.sender.msgs) == 0

        @timeit
        @incr_count
        def ordering_2(x, y):
            return x + y

        ordering_2(5, 6)
        msgs = [json.loads(m) for m in CLIENT_WRAPPER.client.sender.msgs]
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
        assert isinstance(CLIENT_WRAPPER.client, MetlogClient)


class TestRebindMethods(unittest.TestCase):
    def setUp(self):
        client = client_from_text_config("""
        [test1]
        enabled=true
        sender_class=metlog.senders.DebugCaptureSender
        """, 'test1')
        CLIENT_WRAPPER.client = client

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


class TestDecoratorArgs(unittest.TestCase):
    def setUp(self):
        client = client_from_text_config("""
        [test1]
        enabled=true
        sender_class=metlog.senders.DebugCaptureSender
        """, 'test1')
        CLIENT_WRAPPER.client = client

    def test_arg_incr(self):
        '''
        Test incr_count support arguments
        '''
        CLIENT_WRAPPER.client.sender.msgs.clear()
        assert len(CLIENT_WRAPPER.client.sender.msgs) == 0

        @incr_count(name='qdo.foo', count=5, timestamp=0, logger='somelogger', severity=2)
        def simple(x, y):
            return x + y

        simple(5, 6)
        msgs = [json.loads(m) for m in CLIENT_WRAPPER.client.sender.msgs]
        assert len(msgs) == 1
        actual= msgs[0]

        expected = {'severity': 2, 'timestamp': 0,
                    'fields': {'name': 'qdo.foo'},
                    'logger': 'somelogger', 'type': 'counter',
                    'payload': '5', 'env_version': '0.8'}
        assert actual == expected

        @incr_count(name='qdo.foo', count=5, timestamp=0, logger='somelogger',
                severity=2, bad_arg=42)
        def invalid(x, y):
            return x + y

        try:
            invalid(3, 5)
            raise AssertionError("bad_arg should've been rejected")
        except TypeError, te:
            pass

    def test_arg_timeit(self):
        '''
        Test timeit support arguments
        '''
        CLIENT_WRAPPER.client.sender.msgs.clear()
        assert len(CLIENT_WRAPPER.client.sender.msgs) == 0

        @timeit(name='qdo.timeit', timestamp=8231, logger='timeit_logger',
                severity=5, fields={'anumber': 42, 'atext': 'foo'}, rate=7)
        def simple(x, y):
            return x + y

        simple(5, 6)
        msgs = [json.loads(m) for m in CLIENT_WRAPPER.client.sender.msgs]
        assert len(msgs) == 1 

        actual = msgs[0]
        expected = {'severity': 5, 'timestamp': 8231, 'fields': {'anumber': 42, 'rate': 7,
            'name': 'qdo.timeit', 'atext': 'foo'}, 'logger': 'timeit_logger',
            'type': 'timer', 'payload': '0', 'env_version': '0.8'}
        assert actual == expected


        @timeit(name='qdo.timeit', timestamp=8231, logger='timeit_logger',
                severity=5, fields={'anumber': 42, 'atext': 'foo'}, bad_arg=7)
        def invalid(x, y):
            return x + y

        try:
            invalid(3, 5)
            raise AssertionError("bad_arg should've been rejected")
        except TypeError, te:
            pass

