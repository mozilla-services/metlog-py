# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Victor Ng (vng@mozilla.com)
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
import socket
import os

from metlog.config import client_from_dict_config
from metlog.client import MetlogClient
from metlog.decorators import incr_count
from metlog.decorators import timeit
from metlog.holder import CLIENT_HOLDER
from nose.tools import eq_, raises

try:
    import simplejson as json
except:
    import json   # NOQA


@timeit
def timed_add(x, y):
    return x + y


class DecoratorTestBase(object):
    client_name = '_decorator_test'

    def setUp(self):
        self.orig_default_client = CLIENT_HOLDER.global_config.get('default')
        client = CLIENT_HOLDER.get_client(self.client_name)
        client_config = {
            'sender_class': 'metlog.senders.DebugCaptureSender',
            }
        self.client = client_from_dict_config(client_config, client)
        CLIENT_HOLDER.set_default_client_name(self.client_name)

    def tearDown(self):
        del CLIENT_HOLDER._clients[self.client_name]
        CLIENT_HOLDER.set_default_client_name(self.orig_default_client)
        timed_add._client = None


class TestCannedDecorators(DecoratorTestBase):
    def test_module_scope_multiple1(self):
        eq_(timed_add(3, 4), 7)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 1)

    def test_module_scope_multiple2(self):
        eq_(timed_add(4, 5), 9)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 1)

    def test_passed_decorator_args(self):
        name = 'different.timer.name'

        @timeit(name)
        def timed_fn(x, y):
            return x + y

        eq_(timed_fn(3, 5), 8)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        msg = msgs[-1]
        eq_(msg['type'], 'timer')
        eq_(msg['fields']['name'], name)

    def test_decorator_ordering(self):
        @incr_count
        @timeit
        def ordering_1(x, y):
            return x + y

        eq_(ordering_1(5, 6), 11)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 2)

        for msg in msgs:
            expected = 'metlog.tests.test_decorators.ordering_1'
            eq_(msg['fields']['name'], expected)

        # First msg should be counter, then timer as decorators are
        # applied inside to out, but execution is outside -> in
        eq_(msgs[0]['type'], 'timer')
        eq_(msgs[1]['type'], 'counter')

        self.client.sender.msgs.clear()

        @timeit
        @incr_count
        def ordering_2(x, y):
            return x + y

        ordering_2(5, 6)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 2)

        for msg in msgs:
            expected = 'metlog.tests.test_decorators.ordering_2'
            eq_(msg['fields']['name'], expected)

        # Ordering of log messages should occur in the in->out
        # ordering of decoration
        eq_(msgs[0]['type'], 'counter')
        eq_(msgs[1]['type'], 'timer')

    def test_decorating_methods_in_a_class(self):
        class Stub(object):

            def __init__(self, value):
                self.value = value

            @incr_count
            @timeit
            def get_value(self):
                return self.value

        stub = Stub(7)
        eq_(stub.get_value(), 7)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 2)

        for msg in msgs:
            expected = 'metlog.tests.test_decorators.get_value'
            eq_(msg['fields']['name'], expected)

        # First msg should be counter, then timer as decorators are
        # applied inside to out, but execution is outside -> in
        eq_(msgs[0]['type'], 'timer')
        eq_(msgs[1]['type'], 'counter')

        self.client.sender.msgs.clear()

    def test_decorating_two_methods(self):
        class Stub(object):

            def __init__(self, value):
                self.value = value

            @timeit
            def get_value1(self):
                return self.value

            @timeit
            def get_value2(self):
                return self.value

        value = 7
        stub = Stub(value)
        eq_(stub.get_value1(), value)
        eq_(stub.get_value2(), value)
        eq_(stub.get_value1(), value)
        eq_(stub.get_value2(), value)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 4)
        eq_(msgs[0]['fields']['name'],
            'metlog.tests.test_decorators.get_value1')
        eq_(msgs[1]['fields']['name'],
            'metlog.tests.test_decorators.get_value2')


class TestDecoratorArgs(DecoratorTestBase):
    def test_arg_incr(self):
        @incr_count(name='qdo.foo', count=5, timestamp=0, logger='somelogger',
                    severity=2)
        def simple(x, y):
            return x + y

        simple(5, 6)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 1)

        expected = {'severity': 2, 'timestamp': 0,
                    'fields': {'name': 'qdo.foo',
                        'rate': 1.0,
                        },
                    'logger': 'somelogger', 'type': 'counter',
                    'payload': '5', 'env_version': MetlogClient.env_version,
                    'metlog_hostname': socket.gethostname(),
                    'metlog_pid': os.getpid(),
                    }
        eq_(msgs[0], expected)

    @raises(TypeError)
    def test_arg_incr_bad(self):
        @incr_count(name='qdo.foo', count=5, timestamp=0, logger='somelogger',
                severity=2, bad_arg=42)
        def invalid(x, y):
            return x + y

        invalid(3, 5)

    def test_arg_timeit(self):
        @timeit(name='qdo.timeit', timestamp=8231, logger='timeit_logger',
                severity=5, fields={'anumber': 42, 'atext': 'foo'}, rate=7)
        def simple(x, y):
            return x + y

        simple(5, 6)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 1)

        expected = {'severity': 5, 'timestamp': 8231,
                    'fields': {'anumber': 42, 'rate': 7,
                               'name': 'qdo.timeit', 'atext': 'foo',
                               },
                    'logger': 'timeit_logger', 'type': 'timer',
                    'payload': '0', 'env_version': MetlogClient.env_version,
                    'metlog_hostname': socket.gethostname(),
                    'metlog_pid': os.getpid(),
                    }
        eq_(msgs[0], expected)

    @raises(TypeError)
    def test_arg_timeit_bad(self):
        @timeit(name='qdo.timeit', timestamp=8231, logger='timeit_logger',
                severity=5, fields={'anumber': 42, 'atext': 'foo'}, bad_arg=7)
        def invalid(x, y):
            return x + y

        invalid(3, 5)


class TestDisabledDecorators(DecoratorTestBase):
    def test_timeit_disabled(self):
        global_config = CLIENT_HOLDER.global_config
        orig_disabled = global_config.get('disabled_decorators')
        global_config['disabled_decorators'] = set(['timeit'])

        @timeit
        def simple(x, y):
            return x + y

        simple(5, 6)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 0)
        global_config['disabled_decorators'] = orig_disabled

    def test_specific_timer_disabled(self):
        @timeit
        def simple(x, y):
            return x + y

        @timeit
        def simple2(x, y):
            return x + y

        omit = ('metlog.tests.test_decorators.simple')
        self.client._disabled_timers = set([omit])

        simple(1, 2)
        simple2(3, 4)
        msgs = [json.loads(m) for m in self.client.sender.msgs]
        eq_(len(msgs), 1)
        eq_(msgs[0]['fields']['name'], 'metlog.tests.test_decorators.simple2')
