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
#   James Socol (james@mozilla.com)
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from __future__ import absolute_import
import os
import random
import socket
import sys
import threading
import time
import traceback
import types

from datetime import datetime
from functools import wraps
from metlog.senders import NoSendSender


class SEVERITY:
    '''
    Put a namespace around RFC 3164 syslog messages
    '''
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFORMATIONAL = 6
    DEBUG = 7


class _NoOpTimer(object):
    """
    A bogus timer object that will act as a contextdecorator but which
    doesn't actually do anything.
    """
    def __init__(self):
        self.start = None
        self.result = None

    def __call__(self, fn):
        return fn

    def __enter__(self):
        return self

    def __exit__(self, typ, value, tb):
        return False


class _Timer(object):
    """A contextdecorator for timing."""

    def __init__(self, client, name, msg_data):
        # most attributes on a _Timer object should be threadlocal, except for
        # a few which we put directly in the __dict__
        self.__dict__['client'] = client
        self.__dict__['_local'] = threading.local()
        self.__dict__['name'] = name
        self.msg_data = msg_data

    def __delattr__(self, attr):
        """Store thread-local data safely."""
        delattr(self._local, attr)

    def __getattr__(self, attr):
        """Store thread-local data safely."""
        return getattr(self._local, attr)

    def __setattr__(self, attr, value):
        """Store thread-local data safely."""
        setattr(self._local, attr, value)

    def __call__(self, fn):
        """
        Support for use as a decorator.
        """
        if not callable(fn):
            # whoops, can't decorate if we're not callable
            raise ValueError('Timer objects can only wrap callable objects.')

        @wraps(fn)
        def wrapped(*a, **kw):
            with self:
                return fn(*a, **kw)
        return wrapped

    def __enter__(self):
        self.start = time.time()
        self.result = None
        return self

    def __exit__(self, typ, value, tb):
        elapsed = time.time() - self.start
        elapsed = int(round(elapsed * 1000))  # Convert to ms.
        self.result = elapsed
        self.client.timer_send(self.name, elapsed, **self.msg_data)
        return False


class MetlogClient(object):
    """
    Client class encapsulating metlog API, and providing storage for default
    values for various metlog call settings.
    """
    # envelope version, only changes when the message format changes
    env_version = '0.8'

    def __init__(self, sender, logger, severity=6,
                 disabled_timers=None, filters=None):
        """
        :param sender: A sender object used for actual message delivery.
        :param logger: Default `logger` value for all sent messages.
                       This is commonly set to be the name of the
                       current application and is not modified for
                       different instances of metlog within the
                       scope of the same application.
        :param severity: Default `severity` value for all sent messages.
        :param disabled_timers: Sequence of string tokens identifying timers
                                that should be deactivated.
        :param filters: A sequence of filter callables.
        """
        self.setup(sender, logger, severity, disabled_timers, filters)
        self._dynamic_methods = {}
        self._timer_obs = {}
        self._noop_timer = _NoOpTimer()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()

        # seed random for rate calculations
        random.seed()

    def setup(self, sender=None, logger='', severity=6, disabled_timers=None,
              filters=None):
        """
        :param sender: A sender object used for actual message delivery.
        :param logger: Default `logger` value for all sent messages.
        :param severity: Default `severity` value for all sent messages.
        :param disabled_timers: Sequence of string tokens identifying timers
                                that should be deactivated.
        :param filters: A sequence of filter callables.
        """
        if sender is None:
            sender = NoSendSender()
        self.sender = sender
        self.logger = logger
        self.severity = severity

        if disabled_timers is None:
            self._disabled_timers = set()
        elif isinstance(disabled_timers, types.StringTypes):
            self._disabled_timers = set([disabled_timers])
        else:
            self._disabled_timers = set(disabled_timers)
        if filters is None:
            filters = list()
        self.filters = filters

    @property
    def is_active(self):
        """
        Is this client ready to transmit messages? For now we assume that if
        the default sender (i.e. `NoSendSender`) has been replaced then we're
        good to go.
        """
        return not isinstance(self.sender, NoSendSender)

    def send_message(self, msg):
        """
        Apply any filters and, if required, pass message along to the sender
        for delivery.
        """
        for filter_fn in self.filters:
            if not filter_fn(msg):
                return
        try:
            self.sender.send_message(msg)
        except StandardError, e:
            unicode_msg = unicode(str(msg), errors='ignore')

            err_msg = "Error sending message (%s): [%s]" % \
                    (repr(e), unicode_msg.encode("utf8"))
            sys.stderr.write(err_msg)
            return

    def add_method(self, method, override=False):
        """
        Add a custom method to the MetlogClient instance.

        :param method: Callable that will be used as the method.
        :param override: Set this to the method name you want to
                         override. False indicates no override will
                         occur.
        """
        assert isinstance(method, types.FunctionType)

        # Obtain the metlog name directly from the method
        name = method.metlog_name
        if isinstance(override, basestring):
            name = override

        if override is False and hasattr(self, name):
            msg = "The name [%s] is already in use" % name
            raise SyntaxError(msg)

        self._dynamic_methods[name] = method
        meth = types.MethodType(method, self, self.__class__)
        setattr(self, name, meth)

    def metlog(self, type, timestamp=None, logger=None, severity=None,
               payload='', fields=None):
        """
        Create a single message and pass it to the sender for delivery.

        :param type: String token identifying the type of message payload.
        :param timestamp: Time at which the message is generated.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC 5424.
        :param payload: Actual message contents.
        :param fields: Arbitrary key/value pairs for add'l metadata.
        """
        timestamp = timestamp if timestamp is not None else datetime.utcnow()
        logger = logger if logger is not None else self.logger
        severity = severity if severity is not None else self.severity
        fields = fields if fields is not None else dict()

        if hasattr(timestamp, 'isoformat'):
            timestamp = timestamp.isoformat()
        full_msg = dict(type=type, timestamp=timestamp, logger=logger,
                        severity=severity, payload=payload, fields=fields,
                        env_version=self.env_version,
                        metlog_pid=self.pid,
                        metlog_hostname=self.hostname)
        self.send_message(full_msg)

    def timer(self, name, timestamp=None, logger=None, severity=None,
              fields=None, rate=1.0):
        """
        Return a timer object that can be used as a context manager or a
        decorator, generating a metlog 'timer' message upon exit.

        :param name: Required string label for the timer.
        :param timestamp: Time at which the message is generated.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC 5424.
        :param fields: Arbitrary key/value pairs for add'l metadata.
        :param rate: Sample rate, btn 0 & 1, inclusive (i.e. .5 = 50%). Sample
                     rate is enforced in this method, i.e. if a sample rate is
                     used then some percentage of the timers will do nothing.
        """
        # check if timer(s) is(are) disabled or if we exclude for sample rate
        if ((self._disabled_timers.intersection(set(['*', name]))) or
            (rate < 1.0 and random.random() >= rate)):
            return self._noop_timer
        msg_data = dict(timestamp=timestamp, logger=logger, severity=severity,
                        fields=fields, rate=rate)
        if name in self._timer_obs:
            timer = self._timer_obs[name]
            timer.msg_data = msg_data
        else:
            timer = _Timer(self, name, msg_data)
            self._timer_obs[name] = timer
        return timer

    def timer_send(self, name, elapsed, timestamp=None, logger=None,
                   severity=None, fields=None, rate=1.0):
        """
        Converts timing data into a metlog message for delivery.

        :param name: Required string label for the timer.
        :param elapsed: Elapsed time of the timed event, in ms.
        :param timestamp: Time at which the message is generated.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC 5424.
        :param fields: Arbitrary key/value pairs for add'l metadata.
        :param rate: Sample rate, btn 0 & 1, inclusive (i.e. .5 = 50%). Sample
                     rate is *NOT* enforced in this method, i.e. all messages
                     will be sent through to metlog, sample rate is purely
                     informational at this point.
        """
        payload = str(elapsed)
        fields = fields if fields is not None else dict()
        fields.update({'name': name, 'rate': rate})
        self.metlog('timer', timestamp, logger, severity, payload, fields)

    def incr(self, name, count=1, timestamp=None, logger=None, severity=None,
             fields=None, rate=1.0):
        """
        Sends an 'increment counter' message.

        :param name: String label for the counter.
        :param count: Integer amount by which to increment the counter.
        :param timestamp: Time at which the message is generated.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC 5424.
        :param fields: Arbitrary key/value pairs for add'l metadata.
        """
        if rate < 1 and random.random() >= rate:
            return
        payload = str(count)
        fields = fields if fields is not None else dict()
        fields['name'] = name
        fields['rate'] = rate
        self.metlog('counter', timestamp, logger, severity, payload, fields)

    # Standard Python logging API emulation
    def _oldstyle(self, severity, msg, *args, **kwargs):
        """Do any necessary string formatting and then generate the msg"""
        # if `args` is a mapping then extract it
        if (len(args) == 1 and hasattr(args[0], 'keys')
            and hasattr(args[0], '__getitem__')):
            args = args[0]
        if args:
            msg = msg % args
        exc_info = kwargs.get('exc_info', False)
        if exc_info:
            if not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
            tb_lines = traceback.format_exception(exc_info[0], exc_info[1],
                                                  exc_info[2])
            s = ''.join(tb_lines)
            if s[-1:] == '\n':
                s = s[:-1]
            if msg[-1:] != '\n':
                msg = msg + '\n'
            try:
                msg = msg + s
            except UnicodeError:
                msg = msg + s.decode(sys.getfilesystemencoding())
        self.metlog(type='oldstyle', severity=severity, payload=msg)

    def debug(self, msg, *args, **kwargs):
        """ Log a DEBUG level message """
        self._oldstyle(SEVERITY.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """ Log an INFO level message """
        self._oldstyle(SEVERITY.INFORMATIONAL, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        """ Log a WARN level message """
        self._oldstyle(SEVERITY.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """ Log an ERROR level message """
        self._oldstyle(SEVERITY.ERROR, msg, *args, **kwargs)

    def exception(self, msg, exc_info=True, *args, **kwargs):
        """ Log an ALERT level message """
        self._oldstyle(SEVERITY.ALERT, msg, exc_info=exc_info, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """ Log a CRITICAL level message """
        self._oldstyle(SEVERITY.CRITICAL, msg, *args, **kwargs)
