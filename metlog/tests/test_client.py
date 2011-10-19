# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is metlog
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
from datetime import datetime
from metlog.client import MetlogClient
from mock import Mock
from nose.tools import eq_, ok_

import json
import threading
import time


class TestMetlogClient(object):
    logger = 'tests'

    def setUp(self):
        self.mock_sender = Mock()
        self.client = MetlogClient(self.mock_sender, self.logger)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.client.timer._local = threading.local()

    def tearDown(self):
        del self.mock_sender

    def _extract_full_msg(self):
        json_msg = self.mock_sender.send_message.call_args[0][0]
        return json.loads(json_msg)

    def test_metlog_bare(self):
        payload = 'this is a test'
        before = datetime.utcnow().isoformat()
        msgtype = 'testtype'
        self.client.metlog(msgtype, payload=payload)
        after = datetime.utcnow().isoformat()
        full_msg = self._extract_full_msg()
        # check the payload
        eq_(full_msg['payload'], payload)
        # check the various default values
        ok_(before < full_msg['timestamp'] < after)
        eq_(full_msg['type'], msgtype)
        eq_(full_msg['severity'], self.client.severity)
        eq_(full_msg['logger'], self.logger)
        eq_(full_msg['fields'], dict())
        eq_(full_msg['env_version'], self.client.env_version)

    def test_metlog_full(self):
        metlog_args = dict(payload='this is another test',
                           timestamp=datetime.utcnow(),
                           logger='alternate',
                           severity=2,
                           fields={'foo': 'bar',
                                   'boo': 'far'})
        msgtype = 'bawlp'
        self.client.metlog(msgtype, **metlog_args)
        full_msg = self._extract_full_msg()
        metlog_args.update({'type': msgtype,
                            'env_version': self.client.env_version,
                            'timestamp': metlog_args['timestamp'].isoformat()})
        eq_(full_msg, metlog_args)

    def test_timer_contextmanager(self):
        name = 'test'
        with self.client.timer(name) as result:
            time.sleep(0.01)

        ok_(result.ms >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], str(result.ms))
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

    def test_timer_decorator(self):
        name = 'test'
        @self.client.timer(name)
        def timed():
            time.sleep(0.01)

        ok_(not self.mock_sender.send_message.called)
        timed()
        full_msg = self._extract_full_msg()
        ok_(int(full_msg['payload']) >= 10)
        eq_(full_msg['type'], 'timer')
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['fields']['rate'], 1)

    def test_timer_with_rate(self):
        name = 'test'

        @self.client.timer(name, rate=0.01)
        def timed():
            time.sleep(0.001)

        for i in range(10):
            timed()

        # this is a weak test, but not quite sure how else to
        # test explicitly random behaviour
        ok_(self.mock_sender.send_message.call_count < 10)

    def test_incr(self):
        name = 'incr'
        self.client.incr(name)
        full_msg = self._extract_full_msg()
        eq_(full_msg['type'], 'counter')
        eq_(full_msg['logger'], self.logger)
        eq_(full_msg['fields']['name'], name)
        eq_(full_msg['payload'], '1')

        self.client.incr(name, 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg['payload'], '10')
