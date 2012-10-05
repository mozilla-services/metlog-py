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
from metlog.config import client_from_dict_config
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


def test_global_config():
    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.DebugCaptureSender
    global_foo = bar
    global_multi = one
                   two
    """
    client_from_text_config(cfg_txt, 'metlog')
    from metlog.holder import CLIENT_HOLDER
    expected = {'foo': 'bar', 'multi': ['one', 'two']}
    eq_(expected, CLIENT_HOLDER.global_config)


def test_filters_config():
    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.DebugCaptureSender
    [metlog_filter_sev_max]
    provider = metlog.filters.severity_max_provider
    severity = 6
    [metlog_filter_type_whitelist]
    provider = metlog.filters.type_whitelist_provider
    types = foo
            bar
            baz
    """
    client = client_from_text_config(cfg_txt, 'metlog')
    eq_(len(client.filters), 2)

    severity_max = client.filters[0]
    eq_(severity_max.func_name, 'severity_max')
    msg = {'severity': 6}
    ok_(severity_max(msg))
    msg = {'severity': 7}
    ok_(not severity_max(msg))

    type_whitelist = client.filters[1]
    eq_(type_whitelist.func_name, 'type_whitelist')
    msg = {'type': 'bar'}
    ok_(type_whitelist(msg))
    msg = {'type': 'bawlp'}
    ok_(not type_whitelist(msg))


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
    eq_(actual, expected)


def test_handshake_sender_no_backend():
    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.zmq.ZmqHandshakePubSender
    sender_handshake_bind = tcp://localhost:5180
    sender_connect_bind = tcp://localhost:5190
    sender_handshake_timeout = 200
    sender_hwm = 100
    """
    import json
    import sys   # NOQA
    msg = {'milk': 'shake'}
    expected = "%s\n" % json.dumps(msg)
    with patch('sys.stderr') as mock_stderr:
        with patch('metlog.senders.zmq.Pool.start_reconnecting'):
            client = client_from_text_config(cfg_txt, 'metlog')
            client.send_message(msg)
            eq_(mock_stderr.write.call_count, 1)
            eq_(mock_stderr.flush.call_count, 1)
            call_args = mock_stderr.write.call_args[0]
            eq_(call_args[0], expected)


def test_handshake_sender_with_backend():
    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.zmq.ZmqHandshakePubSender
    sender_handshake_bind = tcp://localhost:5180
    sender_connect_bind = tcp://localhost:5190
    sender_handshake_timeout = 200
    sender_hwm = 100
    sender_livecheck = 30
    """
    import json
    import sys   # NOQA

    # Redirect stderr
    with patch('sys.stderr') as mock_stderr:

        # Patch the reconnect_clients call so that we don't spawn a
        # background thread to bind to a server
        with patch('metlog.senders.zmq.Pool.start_reconnecting'):

            client = client_from_text_config(cfg_txt, 'metlog')

            # Now patch the ZmqHandshakePubSender and replace the pool
            # with a mock - this will make sure that all requests to
            # obtain a new 0mq socket will just pass so nothing will
            # go to stderr
            eq_(client.sender.pool._livecheck, 30)
            with patch.object(client.sender, 'pool') as mock_pool:
                msg = {'milk': 'shake'}

                # Note that this JSON dump does *not* have a newline appended
                # to it.  Only JSON messages to stderr have the newline
                expected = json.dumps(msg)

                client.send_message(msg)
                eq_(mock_stderr.write.call_count, 0)
                eq_(mock_stderr.flush.call_count, 0)

            # Check that we called send once with the proper JSON
            # string to the pool
            eq_(mock_pool.send.call_count, 1)
            call_args = mock_pool.send.call_args[0]
            eq_(call_args[0], expected)


def test_plugin_override():
    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.DebugCaptureSender

    [metlog_plugin_exception]
    override=True
    provider=metlog.tests.plugin:config_plugin
    """
    client = client_from_text_config(cfg_txt, 'metlog')
    eq_('dummy', client.dummy.metlog_name)

    cfg_txt = """
    [metlog]
    sender_class = metlog.senders.DebugCaptureSender
    [metlog_plugin_exception]
    provider=metlog.tests.plugin_exception:config_plugin
    """
    # Failure to set an override argument will throw an exception
    assert_raises(SyntaxError, client_from_text_config, cfg_txt, 'metlog')


def test_load_config_multiple_times():
    cfg = {'logger': 'addons-marketplace-dev',
           'sender': {'class': 'metlog.senders.UdpSender',
           'host': ['logstash1', 'logstash2'],
           'port': '5566'}}

    client_from_dict_config(cfg)
    client_from_dict_config(cfg)
