# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import random
import threading
import time
import types
from metlog.path import DottedNameResolver

from datetime import datetime
from functools import wraps


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


class MetlogClient(object):
    """
    Client class encapsulating metlog API, and providing storage for default
    values for various metlog call settings.
    """
    env_version = '0.8'

    def __init__(self, sender, logger='', severity=6):
        self.sender = sender
        self.logger = logger
        self.severity = severity
        self._dynamic_methods = {}

    def send_message(self, msg):
        # Just a handy shortcut so that proxies don't have to talk to
        # the sender attribute
        self.sender.send_message(msg)

    def add_method(self, name, method):
        """ Extend the MetlogClient with a new method and bind it. """

        assert isinstance(method, types.FunctionType)
        if name in dir(self):
            msg = "The name [%s] is already bound into the proxy" % name
            raise SyntaxError(msg)

        self._dynamic_methods[name] = method

        meth = types.MethodType(method, self, self.__class__)
        self.__dict__[name] = meth

    @property
    def timer(self):
        return _Timer(self)

    def metlog(self, type, timestamp=None, logger=None, severity=None,
               payload='', fields=None):
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
        payload = str(count)
        fields = fields if fields is not None else dict()
        fields['name'] = name
        self.metlog('counter', timestamp, logger, severity, payload, fields)


class ClientFactory(object):
    '''
    This class generates a MetlogClient instance wrapped in a proxy
    class with caller specified extensions
    '''

    @classmethod
    def client(cls, sender_clsname, sender_args=[], sender_kwargs={}, extensions={}):
        """
        Configure a sender and extensions to Metlog in one shot
        """
        resolver = DottedNameResolver()
        sender_cls = resolver.resolve(sender_clsname)

        mclient = MetlogClient(sender=sender_cls(*sender_args, **sender_kwargs))

        for name, func_name in extensions.items():
            func = resolver.resolve(func_name)
            mclient.add_method(name, func)

        return mclient
