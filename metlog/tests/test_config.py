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
