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
from metlog.client import MetlogClient
from metlog.config import client_from_dict_config
from metlog.decorators.util import return_fq_name
try:
    import json
except:
    import simplejson as json


class MetlogClientWrapper(object):
    """
    This class acts as a lazy proxy of sorts to the MetlogClient. We need this
    to provide late binding of the MetlogClient so that decorators which use
    Metlog have a chance to be configured prior to affecting the callable which
    is being decorated.
    """
    def __init__(self):
        self.reset()

    def activate(self, client_config):
        """
        Applies configuration to the wrapped client, allowing it to be used and
        activating any Metlog decorators that might be in use.

        :param client_config: Dictionary containing MetlogClient configuration.
        """
        client_from_dict_config(client_config, client=self.client)
        disabled_decorators = [k.replace("disable_", '')
                               for (k, v) in client_config.items()
                               if (k.startswith('disable_') and v)]
        self._disabled_decorators = set(disabled_decorators)
        self.is_activated = True

    def reset(self):
        """
        Sets client related instance variables to default settings.
        """
        self.client = MetlogClient()
        self._disabled_decorators = set()
        self.is_activated = False

    def decorator_is_disabled(self, name):
        # Check if this particular logger is disabled
        return name in self._disabled_decorators

CLIENT_WRAPPER = MetlogClientWrapper()


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
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # bare decorator, i.e. no arguments
            self.args = None
            self.kwargs = None
            self.set_fn(args[0])
        else:
            # we're instantiated w/ arguments that will need to be passed on to
            # the actual metlog call
            self.args = args[1:]
            self.kwargs = kwargs
            self.set_fn(None)

    @property
    def decorator_name(self):
        return self.__class__.__name__

    def predicate(self):
        """
        Called during the rebind process. True return value will rebind such
        that `self.metlog_call` becomes the decorator function, False will
        rebind such that `self._invoke` becomes the decorator function.
        """
        if not CLIENT_WRAPPER.is_activated:
            return False
        if CLIENT_WRAPPER.decorator_is_disabled(self.decorator_name):
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

        key = (self.__class__, self.args, sorted_kw)

        self._metlog_decorators.add(key)

        # Add any decorators from the wrapped callable
        if hasattr(self._fn, '_metlog_decorators'):
            self._metlog_decorators.update(self._fn._metlog_decorators)

    def __call__(self, *args, **kwargs):
        """
        Sorta dirty stuff happening in here. The first time the wrapped
        function is called, this method will replace itself, so that later
        calls to the wrapped function will invoke a different decorator.
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
        self.__call__ = replacement
        return replacement(*args, **kwargs)

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
