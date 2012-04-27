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
import random
import threading
import time
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


class _TimerResult(object):
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

    def disabled(self):
        if hasattr(self.client, '_disabled_timers'):
            return ('*' in self.client._disabled_timers
                    or self.name in self.client._disabled_timers)
        return False

    def __call__(self, name, timestamp=None, logger=None, severity=None,
                 fields=None, rate=1):
        """
        Performs the actual initialization of the timer object. Note that the
        `name` parameter might be a callable when we are being used as a
        decorator. If this is the case, the timer object must have already been
        initialized or we have an error condition.
        """
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
        if self.disabled():
            return None

        self.start = time.time()
        self.result = _TimerResult()
        return self.result

    def __exit__(self, typ, value, tb):
        if self.disabled():
            return False

        dt = time.time() - self.start
        dt = int(round(dt * 1000))  # Convert to ms.
        self.result.ms = dt
        self.client.timing(self, dt)
        del self.start, self.result  # Clean up.
        return False


class MetlogClient(object):
    """
    Client class encapsulating metlog API, and providing storage for default
    values for various metlog call settings.
    """
    env_version = '0.8'

    def __init__(self, sender=None, logger='', severity=6,
                 disabled_timers=None, filters=None):
        """
        :param sender: A sender object used for actual message delivery.
        :param logger: Default `logger` value for all sent messages.
        :param severity: Default `severity` value for all sent messages.
        :param disabled_timers: Sequence of string tokens identifying timers
                                that should be deactivated.
        :param filters: A sequence of 2-tuples, each containing a filter
                        callable and the config dict to pass in to the callable
                        on each invocation.
        """
        self.setup(sender, logger, severity, disabled_timers, filters)

    def setup(self, sender=None, logger='', severity=6, disabled_timers=None,
              filters=None):
        """
        :param sender: A sender object used for actual message delivery.
        :param logger: Default `logger` value for all sent messages.
        :param severity: Default `severity` value for all sent messages.
        :param disabled_timers: Sequence of string tokens identifying timers
                                that should be deactivated.
        :param filters: A sequence of 2-tuples, each containing a filter
                        callable and the config dict to pass in to the callable
                        on each invocation.
        """
        if sender is None:
            sender = NoSendSender()
        self.sender = sender
        self.logger = logger
        self.severity = severity
        self._dynamic_methods = {}
        if disabled_timers is None:
            self._disabled_timers = set()
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
        for filter_fn, config in self.filters:
            if not filter_fn(self, config, msg):
                return
        self.sender.send_message(msg)

    def add_method(self, name, method):
        """
        Add a custom method to the MetlogClient instance.

        :param name: Name to use for the method.
        :param method: Callable that will be used as the method.
        """
        assert isinstance(method, types.FunctionType)
        if hasattr(self, name):
            msg = "The name [%s] is already in use" % name
            raise SyntaxError(msg)
        self._dynamic_methods[name] = method
        meth = types.MethodType(method, self, self.__class__)
        setattr(self, name, meth)

    @property
    def timer(self):
        """
        Return a timer object that can be used as a context manager or a
        decorator. Returned timer will be initialized w/ the following
        parameters.

        :param name: Required string label for the timer.
        :param timestamp: Time at which the message is generated.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC 5424.
        :param fields: Arbitrary key/value pairs for add'l metadata.
        :param rate: Sample rate, btn 0 & 1, inclusive (i.e. .5 = 50%).
        """
        return _Timer(self)

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
                        env_version=self.env_version)
        self.send_message(full_msg)

    def timing(self, timer, elapsed):
        """
        Converts timing data provided by the Timer object into a metlog
        message for delivery.

        :param timer: Timer object.
        :param elapsed: Elapsed time of the timed event, in ms.
        """
        if timer.rate < 1 and random.random() >= timer.rate:
            return
        payload = str(elapsed)
        fields = timer.fields if timer.fields is not None else dict()
        fields.update({'name': timer.name, 'rate': timer.rate})
        self.metlog('timer', timer.timestamp, timer.logger, timer.severity,
                    payload, fields)

    # TODO: push this down into an extension
    def incr(self, name, count=1, timestamp=None, logger=None, severity=None,
             fields=None):
        """
        Sends an 'increment counter' message.

        :param name: String label for the counter.
        :param count: Integer amount by which to increment the counter.
        :param timestamp: Time at which the message is generated.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC 5424.
        :param fields: Arbitrary key/value pairs for add'l metadata.
        """
        payload = str(count)
        fields = fields if fields is not None else dict()
        fields['name'] = name
        self.metlog('counter', timestamp, logger, severity, payload, fields)

    # Standard Python logging API emulation
    def debug(self, msg):
        """ Log a DEBUG level message """
        self.metlog(type='oldstyle', severity=SEVERITY.DEBUG, payload=msg)

    def info(self, msg):
        """ Log a INFO level message """
        self.metlog(type='oldstyle', severity=SEVERITY.INFORMATIONAL,
                    payload=msg)

    def warn(self, msg):
        """ Log a WARN level message """
        self.metlog(type='oldstyle', severity=SEVERITY.WARNING, payload=msg)

    def error(self, msg):
        """ Log a ERROR level message """
        self.metlog(type='oldstyle', severity=SEVERITY.ERROR, payload=msg)

    def exception(self, msg):
        """ Log a ALERT level message """
        self.metlog(type='oldstyle', severity=SEVERITY.ALERT, payload=msg)

    def critical(self, msg):
        """ Log a CRITICAL level message """
        self.metlog(type='oldstyle', severity=SEVERITY.CRITICAL, payload=msg)
