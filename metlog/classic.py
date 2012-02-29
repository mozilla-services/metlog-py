# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

from metlog.helper import HELPER
from metlog.decorators.util import rebind_dispatcher
from metlog.client import SEVERITY


class SimpleLogger(object):
    '''
    This class provides a simplified interface when you don't need
    access to a raw MetlogClient instance.
    '''

    def __init__(self, logger_name=None):
        if not logger_name:
            logger_name = 'anonymous'
        self._logger_name = logger_name

    @property
    def _client(self):
        return HELPER._client

    def metlog_log(self, msg, level):
        '''
        If metlog is enabled, we're going to send messages here
        '''
        self._client.metlog(type='oldstyle',
                logger=self._logger_name,
                fields={'logtext': msg},
                severity=level)

    @rebind_dispatcher('metlog_log')
    def _log(self, msg, level):
        '''
        This is a no-op method in case metlog is disabled
        '''

    # TODO: The standard python logger style method (debug, info,
    # warn, ...) can be replaced with the metlog extension mechanism
    # using add_method

    def debug(self, msg):
        self._log(msg, SEVERITY.DEBUG)

    def info(self, msg):
        self._log(msg, SEVERITY.INFORMATIONAL)

    def warn(self, msg):
        self._log(msg, SEVERITY.WARNING)

    warning = warn

    def error(self, msg):
        self._log(msg, SEVERITY.ERROR)

    def exception(self, msg):
        self._log(msg, SEVERITY.ALERT)

    def critical(self, msg):
        self._log(msg, SEVERITY.CRITICAL)

logger = SimpleLogger()
