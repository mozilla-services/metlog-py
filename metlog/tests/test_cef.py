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
#
# ***** END LICENSE BLOCK *****
from metlog.client_ext import log_cef
import unittest
from cef import logger

from metlog.client import MetlogClient
from metlog.senders import DebugCaptureSender
from metlog.client import setup_client

try:
    import simplejson as json
except ImportError:
    import json  # NOQA


class TestClientSetup(unittest.TestCase):
    def test_setup(self):
        simple_client = setup_client('metlog.senders.DebugCaptureSender')
        assert isinstance(simple_client, MetlogClient)
        assert isinstance(simple_client.sender, DebugCaptureSender)

    def test_setup_extensions(self):
        simple_client = setup_client( \
                'metlog.senders.DebugCaptureSender',
                extensions={'cef': 'metlog.client_ext.log_cef'})

        assert isinstance(simple_client, MetlogClient)
        assert isinstance(simple_client.sender, DebugCaptureSender)
        #assert simple_client.sender._kwargs == {'foo': 'bar'}
        assert hasattr(simple_client, 'cef')


class TestBasicProxy(unittest.TestCase):
    def test_double_overload(self):
        self.logger = setup_client(\
                'metlog.senders.DebugCaptureSender',
                extensions={'cef': 'metlog.client_ext.log_cef'})

        try:
            self.logger.add_method('cef', log_cef)
            msg = 'Should not have succeded with this extension'
            raise AssertionError(msg)
        except SyntaxError, se:
            assert "already bound" in str(se)


class TestCEFLogger(unittest.TestCase):
    """
    These test cases were ported from the cef library
    """

    def setUp(self):
        self.environ = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_HOST': '127.0.0.1',
                        'PATH_INFO': '/', 'REQUEST_METHOD': 'GET',
                        'HTTP_USER_AGENT': 'MySuperBrowser'}

        self.config = {'cef.version': '0', 'cef.vendor': 'mozilla',
                       'cef.device_version': '3', 'cef.product': 'weave',
                       'cef': True}

        self.logger = setup_client(\
                'metlog.senders.DebugCaptureSender',
                extensions={'cef': 'metlog.client_ext.log_cef'})

        self._warn = []

        def _warning(warn):
            self._warn.append(warn)

        self.old_logger = logger.warning
        logger.warning = _warning

    def tearDown(self):
        logger.warning = self.old_logger

    def _log(self, name, severity, *args, **kw):
        # Capture the output from metlog and clear the internal debug buffer
        self.logger.cef(name, severity, self.environ, self.config, *args, **kw)
        msgs = self.logger.sender.msgs

        msg = json.loads(msgs[0])
        msgs.clear()
        # We only care about the CEF payload
        assert msg['type'] == 'cef'
        return msg['fields']['logtext']

    def test_cef_logging(self):
        # should not fail
        res = self._log('xx|x', 5)
        self.assertEquals(len(res.split('|')), 10)

        # should not fail and be properly escaped
        self.environ['HTTP_USER_AGENT'] = "=|\\"
        content = self._log('xxx', 5)

        cs = 'cs1Label=requestClientApplication cs1=\=|\\\\ '
        self.assertTrue(cs in content)

        # should log.warn because extra keys shouldn't have pipes
        self._log('xxx', 5, **{'ba|d': 1})

        self.assertEqual('The "ba|d" key contains illegal characters',
                         self._warn[0])

    def test_suser(self):
        content = self._log('xx|x', 5, username='me')
        self.assertTrue('suser=me' in content)

    def test_custom_extensions(self):
        content = self._log('xx|x', 5, username='me',
                            custom1='ok')
        self.assertTrue('custom1=ok' in content)

    def test_too_big(self):
        big = 'i' * 500
        bigger = 'u' * 550
        content = self._log('xx|x', 5, username='me',
                            custom1='ok', big=big, bigger=bigger)
        self.assertTrue('big=ii' in content)
        self.assertFalse('bigger=uu' in content)
        self.assertTrue('CEF Message too big' in self._warn[0])

    def test_conversions(self):
        content = self._log('xx\nx|xx\rx', 5, username='me',
                            ext1='ok=ok', ext2='ok\\ok')
        self.assertTrue('xx\\\nx\\|xx\\\rx' in content)
        self.assertTrue("ext1=ok\\=ok ext2=ok\\\\ok" in content)

    def test_default_signature(self):
        content = self._log('xx', 5)
        self.assertTrue('xx|xx' in content)
