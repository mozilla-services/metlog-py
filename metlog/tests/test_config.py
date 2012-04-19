# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from metlog.exceptions import EnvironmentNotFoundError
from metlog.client import MetlogClient
from metlog.config import client_from_text_config
from metlog.senders import DebugCaptureSender
from mock import Mock
from mock import patch
from nose.tools import assert_raises, eq_, ok_
import os


MockSender = Mock()


def test_simple_config():
    cfg_txt = """
    [metlog_config]
    sender_class = metlog.senders.DebugCaptureSender
    """
    client = client_from_text_config(cfg_txt, 'metlog_config')
    eq_(client.__class__, MetlogClient)
    eq_(client.sender.__class__, DebugCaptureSender)


def test_multiline_config():
    cfg_txt = """
    [metlog_config]
    sender_class = metlog.tests.test_config.MockSender
    sender_multi = foo
                   bar
    """
    client = client_from_text_config(cfg_txt, 'metlog_config')
    ok_(isinstance(client.sender, Mock))
    MockSender.assert_called_with(multi=['foo', 'bar'])


def test_environ_vars():
    env_var = 'SENDER_TEST'
    marker = object()
    orig_value = marker
    if env_var in os.environ:
        orig_value = os.environ[env_var]
    os.environ[env_var] = 'metlog.senders.DebugCaptureSender'
    cfg_txt = """
    [test1]
    sender_class = ${SENDER_TEST}
    """
    client = client_from_text_config(cfg_txt, 'test1')
    eq_(client.sender.__class__, DebugCaptureSender)

    cfg_txt = """
    [test1]
    sender_class = ${NO_SUCH_VAR}
    """
    assert_raises(EnvironmentNotFoundError, client_from_text_config,
                  cfg_txt, 'test1')
    if orig_value is not marker:
        os.environ[env_var] = orig_value
    else:
        del os.environ[env_var]


def test_int_bool_conversions():
    cfg_txt = """
    [metlog_config]
    sender_class = metlog.tests.test_config.MockSender
    sender_integer = 123
    sender_true1 = True
    sender_true2 = t
    sender_true3 = Yes
    sender_true4 = on
    sender_false1 = false
    sender_false2 = F
    sender_false3 = no
    sender_false4 = OFF
    """
    client = client_from_text_config(cfg_txt, 'metlog_config')
    ok_(isinstance(client.sender, Mock))
    MockSender.assert_called_with(integer=123, true1=True, true2=True,
                                  true3=True, true4=True, false1=False,
                                  false2=False, false3=False, false4=False)


def test_filters_config():
    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.DebugCaptureSender
    [metlog_filter_sev_max]
    filter = metlog.filters.severity_max
    severity = 6
    [metlog_filter_type_whitelist]
    filter = metlog.filters.type_whitelist
    types = foo
            bar
            baz
    """
    client = client_from_text_config(cfg_txt, 'metlog')
    from metlog.filters import severity_max, type_whitelist
    expected = [(severity_max, {'severity': 6}),
                (type_whitelist, {'types': ['foo', 'bar', 'baz']}),
                ]
    eq_(client.filters, expected)


def test_plugins_config():
    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.DebugCaptureSender
    [metlog_plugin_dummy]
    provider=metlog.tests.plugin:config_plugin
    verbose=True
    foo=bar
    some_list = dog
                cat
                bus
    port=8080
    host=lolcathost
    """
    client = client_from_text_config(cfg_txt, 'metlog')
    actual = client.dummy(verbose=True)
    expected = {'host': 'lolcathost',
     'foo': 'bar', 'some_list': ['dog', 'cat', 'bus'],
     'port': 8080}
    assert actual == expected


def test_handshake_sender_no_backend():
    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.ZmqHandshakePubSender
    sender_handshake_bind = tcp://localhost:5180
    sender_connect_bind = tcp://localhost:5190
    sender_handshake_timeout = 200
    sender_hwm = 100
    """
    import json
    import sys   # NOQA
    client = client_from_text_config(cfg_txt, 'metlog')
    msg = {'milk': 'shake'}
    expected = "%s\n" % json.dumps(msg)
    with patch('sys.stderr') as mock_stderr:
        client.send_message(msg)
        eq_(mock_stderr.write.call_count, 1)
        eq_(mock_stderr.flush.call_count, 1)
        call_args = mock_stderr.write.call_args[0]
        eq_(call_args[0], expected)


from metlog.senders.zmq import ZmqSender
import zmq


class FakeLogstash(ZmqSender):
    @classmethod
    def run(cls):
        syncclient = ZmqSender._zmq_context.socket(zmq.REP)
        syncclient.bind('tcp://*:5180')
        syncclient.recv()
        syncclient.send('')


def test_handshake_sender_with_backend():
    # TODO: add test to make sure that connectinos only send stuff to
    # the socket and not to the stderr output
    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.ZmqHandshakePubSender
    sender_handshake_bind = tcp://localhost:5180
    sender_connect_bind = tcp://localhost:5190
    sender_handshake_timeout = 200
    sender_hwm = 100
    """
    import json
    import sys   # NOQA

    # Startup the fake Logstash
    import threading
    logstash = threading.Thread(target=FakeLogstash.run)
    logstash.daemon = True
    logstash.start()

    client = client_from_text_config(cfg_txt, 'metlog')
    with patch.object(client.sender, 'pool') as mock_pool:
        msg = {'milk': 'shake'}

        # Note that this JSON dump does *not* have a newline appended
        # to it.  Only JSON messages to stderr have the newline
        expected = json.dumps(msg)
        with patch('sys.stderr') as mock_stderr:
            client.send_message(msg)
            eq_(mock_stderr.write.call_count, 0)
            eq_(mock_stderr.flush.call_count, 0)

        eq_(mock_pool.send.call_count, 1)
        call_args = mock_pool.send.call_args[0]
        eq_(call_args[0], expected)
