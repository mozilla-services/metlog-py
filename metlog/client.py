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
# The Original Code is metlog, with a bit of stealing from pystatsd
# (https://github.com/jsocol/pystatsd).
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#   James Socol (james@mozilla.com)
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
import random
import threading
import time
import uuid

from datetime import datetime
from functools import wraps


class TimerResult(object):
    def __init__(self, ms=None):
        self.ms = ms


class _Timer(object):
    """A contextdecorator for timing."""

    def __init__(self, client):
        # We have to make sure the client is attached directly to __dict__
        # because the __setattr__ below is so clever. Otherwise the client
        # becomes a thread-local object even though the connection is for the
        # whole process. This error was witnessed under mod_wsgi when using an
        # ImportScript.
        self.__dict__['client'] = client
        # Have to do the same for the thread local itself, to avoid recursion
        self.__dict__['_local'] = threading.local()
        random.seed()

    def __delattr__(self, attr):
        """Store thread-local data safely."""
        delattr(self._local, attr)

    def __getattr__(self, attr):
        """Store thread-local data safely."""
        return getattr(self._local, attr)

    def __setattr__(self, attr, value):
        """Store thread-local data safely."""
        setattr(self._local, attr, value)

    def __call__(self, name, timestamp=None, logger=None, severity=None,
                 fields=None, rate=1):
        # As a decorator, 'name' may be a function.
        if callable(name):
            # check to make sure we've been through already to set the
            # timer values
            if not hasattr(self, 'name'):
                raise ValueError('Timer instance must be called and provided '
                                 'a `name` value')

            @wraps(name)
            def wrapped(*a, **kw):
                with self:
                    return name(*a, **kw)
            return wrapped

        self.name = name
        self.timestamp = timestamp
        self.logger = logger
        self.severity = severity
        self.fields = fields
        self.rate = rate
        return self

    def __enter__(self):
        if not hasattr(self, 'name'):
            raise ValueError('Timer instance must be called and provided a '
                             '`name` value')
        self.start = time.time()
        self.result = TimerResult()
        return self.result

    def __exit__(self, typ, value, tb):
        dt = time.time() - self.start
        dt = int(round(dt * 1000))  # Convert to ms.
        self.result.ms = dt
        self.client.timing(self, dt)
        del self.start, self.result  # Clean up.
        return False

class SEVERITY(object):
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFORMATIONAL = 6
    DEBUG = 7

class MetlogClient(object):
    """
    Client class encapsulating metlog API, and providing storage for default
    values for various metlog call settings.
    """
    env_version = '0.8'


    def __init__(self, sender, logger='', severity=6, back_channel=None):
        self.sender = sender
        self.back_channel = back_channel
        self.logger = logger
        self.severity = severity

        # UUIDs are usually just matched on prefix, don't panic
        self._uuid = str(uuid.uuid1())

    @property
    def timer(self):
        return _Timer(self)

    def handle_backchannel(self):
        """
        A valid backchannel message has this structure:

        {
            'logger': '' or logger name,
            'uuid': optional UUID prefix if you want fine grained
                    control over individual loggers
            'cmd': one of "LOGGER_NAMES", "SET_SEVERITY", "SET_RATE"
            'value': optional. 0-7 for severity, 0.0-1.0 for rate
            
            # This is the callback point that we need to use to
            # respond to messages
            # TODO:
            'callback': 'ipc://127.0.0.1:6010'
        }

        any invalid cmd tag will be dropped
        """
        if self.back_channel is None:
            return

        blob = self.back_channel.recv_message()

        if blob is None:
            return

        COMMAND_MAP = {
                'LOGGER_INFO': self.get_logger_info,
                'SET_SEVERITY': self.set_severity,
                'SET_RATE': self.set_rate,
                }

        log_name = blob.get('logger', None)
        uuid = blob.get('uuid', None)

        if log_name not in ('', self.logger) and \
                not (uuid and self._uuid.startswith(uuid)):
            # This isn't for us
            return

        try:
            result = COMMAND_MAP[blob['cmd']](blob.get('value', None))
            print "Got result: [%s]" % str(result)
        except KeyError, ke:
            # skip this - it's a malformed message
            pass

    def get_logger_info(self, ignored):
        """
        The logger name is the logger string, a pipe and the uuid
        for the logger
        """
        return {'uuid': self._uuid,
                'logger': self.logger,
                'severity': self.severity,
                }

    def set_severity(self, value):
        if not isinstance(value, int) or not (0 <= value <= 7):
            # TODO: this should probably do something else
            self.incr("set_severity_fail", severity=SEVERITY.WARNING)
            return
        self.severity = value

    def set_rate(self, value):
        if not isinstance(value, float) or not (0 <= value <= 1):
            # TODO: this should probably do something else
            self.incr("set_rate_fail", severity=SEVERITY.WARNING)
            return
        self.rate = value

    def metlog(self, type, timestamp=None, logger=None, severity=None,
               payload='', fields=None):

        self.handle_backchannel()

        timestamp = timestamp if timestamp is not None else datetime.utcnow()
        logger = logger if logger is not None else self.logger
        severity = severity if severity is not None else self.severity
        fields = fields if fields is not None else dict()
        if hasattr(timestamp, 'isoformat'):
            timestamp = timestamp.isoformat()
        full_msg = dict(type=type, timestamp=timestamp, logger=logger,
                        severity=severity, payload=payload, fields=fields,
                        env_version=self.env_version)
        self.sender.send_message(full_msg)

    def timing(self, timer, elapsed):
        self.handle_backchannel()

        if timer.rate < 1 and random.random() >= timer.rate:
            return
        payload = str(elapsed)
        fields = timer.fields if timer.fields is not None else dict()
        fields.update({'name': timer.name, 'rate': timer.rate})
        self.metlog('timer', timer.timestamp, timer.logger, timer.severity,
                    payload, fields)

    def incr(self, name, count=1, timestamp=None, logger=None, severity=None,
             fields=None):
        payload = str(count)
        fields = fields if fields is not None else dict()
        fields['name'] = name
        self.metlog('counter', timestamp, logger, severity, payload, fields)
