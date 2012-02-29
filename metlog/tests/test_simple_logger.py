# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import unittest
from metlog import logger
from metlog.client import SEVERITY
from metlog.helper import HELPER
from metlog.config import Config

try:
    import simplejson as json
except:
    import json

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
            msgs = [json.loads(m) for m in HELPER._client.sender.msgs]

            assert len(msgs) == 1
            timer_call = msgs[0]
            assert timer_call['logger'] == 'anonymous'
            assert timer_call['type'] == 'oldstyle'
            assert timer_call['fields']['logtext'] == 'some %s' % msg
            assert timer_call['severity'] == lvl

            HELPER._client.sender.msgs.clear()


