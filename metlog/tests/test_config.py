# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

from metlog.config import parse_configobj
from metlog.config import parse_configdict
from StringIO import StringIO
from textwrap import dedent
import ConfigParser


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

    cfg_file = StringIO(dedent("""
    [metlog_config]
    enabled=true
    sender_backend = metlog.sender.ZmqPubSender
    sender_bindstrs=tcp://127.0.0.1:5665/
                    tcp://192.168.1.1:5665/
    """))
    cfg = ConfigParser.ConfigParser()
    cfg.readfp(cfg_file)

    assert EXPECTED == parse_configobj(cfg, 'metlog_config')


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
