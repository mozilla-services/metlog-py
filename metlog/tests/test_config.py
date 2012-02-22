# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

from metlog.exceptions import EnvironmentNotFoundError
from metlog.exceptions import UnknownConfigurationType
from metlog.config import Config
from metlog.config import parse_configobj
from metlog.config import parse_configdict
from StringIO import StringIO
from textwrap import dedent
import ConfigParser
import os


def test_config():
    EXPECTED = {'enabled': True,
            'sender_backend': 'metlog.senders.DebugCaptureSender'}

    cfg_file = StringIO(dedent("""
    [metlog_config]
    enabled=true
    sender_backend=metlog.senders.DebugCaptureSender
    """))

    cfg = ConfigParser.ConfigParser()
    cfg.readfp(cfg_file)

    assert EXPECTED == parse_configobj(cfg, 'metlog_config')


def test_multiline():
    EXPECTED = {'enabled': True,
            'sender_backend': 'metlog.sender.ZmqPubSender',
            'sender_bindstrs': ['tcp://127.0.0.1:5665/',
                               'tcp://192.168.1.1:5665/']}

    cfg_file = Config("""
    [metlog_config]
    enabled=true
    sender_backend = metlog.sender.ZmqPubSender
    sender_bindstrs=tcp://127.0.0.1:5665/
                    tcp://192.168.1.1:5665/
    """, 'metlog_config')
    assert EXPECTED == cfg_file


def test_dictlike():

    EXPECTED = {'enabled': True,
            'sender_backend': 'metlog.sender.ZmqPubSender',
            'sender_bindstrs': ['tcp://127.0.0.1:5665/',
                               'tcp://192.168.1.1:5665/']}
    cfg = {'enabled': True,
            'sender_backend': 'metlog.sender.ZmqPubSender',
            'sender_bindstrs': """tcp://127.0.0.1:5665/
                               tcp://192.168.1.1:5665/"""}

    assert EXPECTED == parse_configdict(cfg)

    cfg = {'enabled': 'true',
            'sender_backend': 'metlog.sender.ZmqPubSender',
            'sender_bindstrs': """tcp://127.0.0.1:5665/
                               tcp://192.168.1.1:5665/"""}

    assert EXPECTED == parse_configdict(cfg)


def test_environ_vars():
    os.environ['METLOG_HOME'] = os.getcwd()
    cfg = Config("""
    [test1]
    enabled=true
    sender_backend=metlog.senders.DebugCaptureSender
    MHOME=${METLOG_HOME}
    """, 'test1')
    assert cfg['mhome'] != None


    try:
        cfg = Config("""
        [test1]
        enabled=true
        sender_backend=metlog.senders.DebugCaptureSender
        MHOME=${NO_SUCH_VAR}
        """, 'test1')

        raise AssertionError("No environment variable of this name should be found")
    except EnvironmentNotFoundError, enf:
        pass

def test_invalid_config_type():
    try:
        cfg = Config(range(5), 'foo')
        raise AssertionError("Configuration should throw an immediate error")
    except UnknownConfigurationType, uct:
        pass

