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
from metlog.decorators.base import CLIENT_WRAPPER, MetlogDecorator
from metlog.decorators.base import rebind_dispatcher


class timeit(MetlogDecorator):
    """
    Lazily decorate any callable with a metlog timer.
    """
    def __init__(self, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            fn = args[0]
            self.set_fn(fn)
            self.kwargs = {'name': self._method_name}
        else:
            self.set_fn(None)
            self.kwargs = kwargs

    def is_timer_enabled(self):
        client = CLIENT_WRAPPER.client
        if client is None:
            # no client -> we shouldn't even get here
            return False
        if self._method_name in CLIENT_WRAPPER.client._disabled_timers:
            return False
        if '*' in CLIENT_WRAPPER.client._disabled_timers:
            return False
        return True

    @rebind_dispatcher('metlog_call', decorator_name='timeit',
                       predicate='is_timer_enabled')
    def __call__(self, *args, **kwargs):
        if self._fn is None and callable(args[0]):
            self.set_fn(args[0])
            return self
        return self._invoke(*args, **kwargs)

    def metlog_call(self, *args, **kwargs):
        if self._fn is None and callable(args[0]):
            self.set_fn(args[0])
            return self

        with CLIENT_WRAPPER.client.timer(**self.kwargs):
            return self._invoke(*args, **kwargs)


class incr_count(MetlogDecorator):
    """
    Lazily decorate any callable w/ a wrapper that will increment a metlog
    counter whenever the callable is invoked.
    """
    def __init__(self, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            fn = args[0]
            self.set_fn(fn)
            self.kwargs = {'name': self._method_name, 'count': 1}
        else:
            self.set_fn(None)
            self.kwargs = kwargs

    @rebind_dispatcher('metlog_call')
    def __call__(self, *args, **kwargs):
        if self._fn is None and callable(args[0]):
            self.set_fn(args[0])
            return self
        return self._invoke(*args, **kwargs)

    def metlog_call(self, *args, **kwargs):
        if self._fn is None and callable(args[0]):
            self.set_fn(args[0])
            return self
        try:
            result = self._invoke(*args, **kwargs)
        finally:
            CLIENT_WRAPPER.client.incr(**self.kwargs)
        return result
