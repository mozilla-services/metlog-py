# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Victor Ng (vng@mozilla.com)
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
"""
This module contains a Metlog decorator base class and some additional helper
code. The primary reason for these abstractions is 'deferred configuration'.
Decorators are evaluated by Python at import time, but often the configuration
needed for a Metlog client, which might negate (or change) the behavior of a
Metlog decorator, isn't available until later, after some config parsing code
has executed. This code provides a mechanism to have a function get wrapped in
one way (or not at all) when the decorator is originally evaluated, but then to
be wrapped differently once the config has loaded and the desired final
behavior has been established.
"""
import functools

from metlog.decorators.util import return_fq_name
from metlog.holder import CLIENT_HOLDER
try:
    import json
except:
    import simplejson as json  # NOQA


class MetlogDecorator(object):
    """
    This is a base class for Metlog decorators, designed to support 'rebinding'
    of the actual decorator method once Metlog configuration has actually been
    loaded. The first time the decorated function is invoked, the `predicate`
    method will be called. If the result is True, then `metlog_call` (intended
    to be implemented by subclasses) will be used as the decorator. If the
    `predicate` returns False, then `_invoke` (which by default does nothing
    but call the wrapped function) will be used as the decorator.
    """
    def __init__(self, *args, **kwargs):
        """
        :param client: Optional MetlogClient instance. Will override any
                       `client_name` value that may be specified, if provided.
        :param client_name: Optional `logger` name of a MetlogClient instance
                            that is stored in the CLIENT_HOLDER

        If neither the `client` nor `client_name` parameters are specified,
        then CLIENT_HOLDER.default_client will be used.
        """
        self._client = kwargs.pop('client', None)
        self.client_name = kwargs.pop('client_name', '')
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # bare decorator, i.e. no arguments
            self.args = None
            self.kwargs = None
            self.set_fn(args[0])
        else:
            # we're instantiated w/ arguments that will need to be passed on to
            # the actual metlog call
            self.args = args
            self.kwargs = kwargs
            self.set_fn(None)

    @property
    def decorator_name(self):
        return self.__class__.__name__

    @property
    def client(self):
        if self._client is None:
            if self.client_name:
                self._client = CLIENT_HOLDER.get_client(self.client_name)
            else:
                self._client = CLIENT_HOLDER.default_client
        return self._client

    def predicate(self):
        """
        Called during the rebind process. True return value will rebind such
        that `self.metlog_call` becomes the decorator function, False will
        rebind such that `self._invoke` becomes the decorator function.
        """
        disabled = CLIENT_HOLDER.global_config.get('disabled_decorators', [])
        if self.decorator_name in disabled:
            return False
        return True

    def set_fn(self, fn):
        """
        Sets the function and stores the full dotted notation fn name for later
        use.

        :param fn: Actual function that we are decorating.
        """
        self._fn = fn
        if fn is None:
            self._fn_fq_name = None
        elif isinstance(fn, MetlogDecorator):
            self._fn_fq_name = fn._fn_fq_name
        else:
            self._fn_fq_name = return_fq_name(fn)

        if self._fn != None:
            self._update_decoratorchain()

    def _update_decoratorchain(self):
        if not hasattr(self, '_metlog_decorators'):
            self._metlog_decorators = set()

        if self.kwargs is None:
            sorted_kw = None
        else:
            sorted_kw = json.dumps(self.kwargs)

        if self.args is None:
            sorted_args = None
        else:
            sorted_args = tuple(self.args)

        key = (self.__class__, sorted_args, sorted_kw)

        self._metlog_decorators.add(key)

        # Add any decorators from the wrapped callable
        if hasattr(self._fn, '_metlog_decorators'):
            self._metlog_decorators.update(self._fn._metlog_decorators)

    def _real_call(self, *args, **kwargs):
        """
        Sorta dirty stuff happening in here. The first time the wrapped
        function is called, this method will replace itself. That means this
        code should only run once per decorated function.
        """
        if (self._fn is None and len(args) == 1 and len(kwargs) == 0
            and callable(args[0])):
            # we were instantiated w/ args, now we have to wrap the function
            self.set_fn(args[0])
            return self
        # we get here in the first actual invocation of the wrapped function
        if self.predicate():
            replacement = self.metlog_call
        else:
            replacement = self._invoke
        self._real_call = replacement
        return replacement(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self._real_call(*args, **kwargs)

    def __get__(self, instance, owner):
        """Descriptor lookup logic to implement bound methods."""
        # If accessed directly from the class, return the decorator itself.
        if instance is None:
            return self
        # If accessed via an instance, bind it as the first argument.
        return functools.partial(self, instance)

    @property
    def __name__(self):
        """Support the use of functools.wraps."""
        return self._fn.__name__

    def _invoke(self, *args, **kwargs):
        """Call the wrapped function."""
        return self._fn(*args, **kwargs)

    def metlog_call(self, *args, **kwargs):
        """Actual metlog activity happens here. Implemented by subclasses."""
        raise NotImplementedError
