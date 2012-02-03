from metlog.proxy import Proxy, log_cef
import unittest
from cef import logger

from metlog.client import MetlogClient
from metlog.senders import DebugCaptureSender


class TestBasicProxy(unittest.TestCase):
    def test_double_overload(self):
        client = MetlogClient(sender=DebugCaptureSender())

        self.logger = Proxy(client)
        self.logger.extend_proxy('cef', log_cef)
        try:
            self.logger.extend_proxy('cef', log_cef)
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

        client = MetlogClient(sender=DebugCaptureSender())

        self.logger = Proxy(client)
        self.logger.extend_proxy('cef', log_cef)

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

        msg = msgs[0]
        msgs.clear()
        # We only care about the CEF payload
        assert msg['type'] == 'cef'
        return msg['payload']

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
