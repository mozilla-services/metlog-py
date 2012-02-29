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
from metlog.exceptions import MethodNotFoundError
import functools


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
        self._disabled_decorators = {}

    def activate(self, client, disabled_decorators):
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
        self._disabled_decorators = set(disabled_decorators)

    @property
    def is_activated(self):
        return self.client is not None

    def decorator_is_disabled(self, name):
        # Check if this particular logger is disabled
        return name in self._disabled_decorators

CLIENT_WRAPPER = MetlogClientWrapper()


def rebind_dispatcher(alt_method_name, decorator_name=None, predicate=None):
    """
    This decorator can only be used on the `__call__` method of a decorator
    class.  It will conditionally rebind an alternate method on the same
    decorator class in place of whatever is returned by the `__call__` method
    if metlog is enabled for the specified decorator name.

    :param alt_method_name: Name of the alternate decorator class method to
                            use in case the rebinding actually happens.
    :param decorator_name: Name of this decorator to be compared against set
                           of disabled metlog decorators (i.e. decorators not
                           to rebind).
    :param predicate: A function that will be called before the rebinding. If
                      the predicate returns a False value, rebinding will not
                      happen. If `predicate` is not a callable, it will be
                      assumed to be the name of a method on the decorator
                      class.
    """
    def wrapped(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            klass = args[0].__class__  # decorator class
            do_rebind = True

            if not CLIENT_WRAPPER.is_activated:
                do_rebind = False
            elif CLIENT_WRAPPER.decorator_is_disabled(decorator_name):
                do_rebind = False
            elif predicate is not None:
                real_pred = predicate
                if not callable(real_pred):
                    real_pred = getattr(args[0], predicate, None)
                    if real_pred is None:
                        msg = 'No such method: [%s]' % predicate
                        raise MethodNotFoundError(msg)
                if not real_pred():
                    do_rebind = False

            if do_rebind:
                # Rebind the alternate method as the decorator instead of the
                # `__call__` method
                alt_method = getattr(klass, alt_method_name, None)
                if not alt_method:
                    msg = 'No such method: [%s]' % alt_method_name
                    raise MethodNotFoundError(msg)
                setattr(klass, func.__name__, alt_method)
                return alt_method(*args, **kwargs)
            else:
                # Retain the `__call__` method as the decorator
                setattr(klass, func.__name__, func)
                return func(*args, **kwargs)

        return inner
    return wrapped


class MetlogDecorator(object):
    """
    This is a base class for Metlog decorators, designed to support 'rebinding'
    of the actual decorated method once Metlog configuration has actually been
    loaded.
    """
    def set_fn(self, fn):
        self._fn = fn
        if self._fn is None:
            return

        if isinstance(fn, MetlogDecorator):
            if hasattr(fn, '_metrics_fn_code'):
                self._metrics_fn_code = fn._metrics_fn_code
            self._method_name = fn._method_name
        else:
            if hasattr(self._fn, 'func_code'):
                self._metrics_fn_code = getattr(self._fn, 'func_code')
            self._method_name = return_fq_name(self._fn)

    @property
    def __name__(self):
        """Support the use of functools.wraps"""
        return self._fn.__name__

    def _invoke(self, *args, **kwargs):
        return self._fn(*args, **kwargs)
