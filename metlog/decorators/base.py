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
This module contains a Metlog decorator base class and some helper functions
and classes. The primary reason for these abstractions is 'deferred
configuration'. Decorators are evaluated by Python at import time, but often
the configuration needed for a Metlog client, which might change (or negate)
the behavior of a Metlog decorator, isn't available until later, after some
config parsing code has executed. This code provides a mechanism to have a
function get wrapped in one way (or not at all) when the decorator is
originally evaluated, but then to be wrapped differently once the config has
loaded and the desired final behavior has been established.
"""
from metlog.decorators.util import return_fq_name


class MetlogClientWrapper(object):
    """
    This class acts as a lazy proxy of sorts to the MetlogClient. We need this
    to provide late binding of the MetlogClient so that decorators which use
    Metlog have a chance to be configured prior to affecting the callable which
    is being decorated.
    """
    def __init__(self):
        self.client = None
        # Track any disabled loggers
        self._disabled_decorators = set()

    def activate(self, client, disabled_decorators=None):
        """
        This method needs to be called to actually enable Metlog decorators
        set up using `_rebind_dispatcher` and the MetlogDecorator base class
        defined below.

        :param client: Fully configured MetlogClient instance.
        :param disabled_decorators: A sequence of strings representing the
                                    names of any Metlog decorator functions
                                    that should not be enabled.
        """
        self.client = client
        if disabled_decorators is None:
            disabled_decorators = []
        self._disabled_decorators = set(disabled_decorators)

    @property
    def is_activated(self):
        return self.client is not None

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
            self.set_fn(args[0])
            self.args = None
            self.kwargs = None
        else:
            # we're instantiated w/ arguments that will need to be passed on to
            # the actual metlog call
            self.set_fn(None)
            self.args = args[1:]
            self.kwargs = kwargs

    @property
    def decorator_name(self):
        return self.__class__.__name__

    def predicate(self):
        if not CLIENT_WRAPPER.is_activated:
            return False
        if CLIENT_WRAPPER.decorator_is_disabled(self.decorator_name):
            return False
        return True

    def set_fn(self, fn):
        """
        Sets the function and stores the full dotted notation fn name for later
        use.
        """
        self._fn = fn
        if fn is None:
            self._fn_fq_name = None
        elif isinstance(fn, MetlogDecorator):
            self._fn_fq_name = fn._fn_fq_name
        else:
            self._fn_fq_name = return_fq_name(fn)

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
