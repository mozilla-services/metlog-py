# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

from metlog.decorators.util import rebind_dispatcher
from metlog.decorators.util import return_fq_name
from metlog.helper import HELPER


class MetricsDecorator(object):
    """
    This is a base class used to store some metadata about the
    decorated function.  This is needed since if you stack decorators,
    you'll lose the name of the underlying function that is being
    logged.  Mostly, we just care about the function name.
    """
    def __init__(self, fn):
        self._fn = fn

        if isinstance(fn, MetricsDecorator):
            if hasattr(fn, '_metrics_fn_code'):
                self._metrics_fn_code = fn._metrics_fn_code
            self._method_name = fn._method_name
        else:
            if hasattr(self._fn, 'func_code'):
                self._metrics_fn_code = getattr(self._fn, 'func_code')
            self._method_name = return_fq_name(self._fn)

    @property
    def __name__(self):
        # This is only here to support the use of functools.wraps
        return self._fn.__name__

    def _invoke(self, *args, **kwargs):
        return self._fn(*args, **kwargs)


class timeit(MetricsDecorator):
    '''
    Decorate any callable for metrics timing.

    You must write you decorator in 'class'-style or else you won't be
    able to have your decorator disabled.
    '''
    def __init__(self, fn):
        MetricsDecorator.__init__(self, fn)

    @rebind_dispatcher('metlog_call', decorator_name='timeit')
    def __call__(self, *args, **kwargs):
        return self._invoke(*args, **kwargs)

    def metlog_call(self, *args, **kwargs):
        with HELPER.timer(self._method_name):
            return self._invoke(*args, **kwargs)


class incr_count(MetricsDecorator):
    '''
    Decorate any callable for metrics timing.
    '''
    def __init__(self, fn):
        MetricsDecorator.__init__(self, fn)

    @rebind_dispatcher('metlog_call')
    def __call__(self, *args, **kwargs):
        return self._invoke(*args, **kwargs)

    def metlog_call(self, *args, **kwargs):
        try:
            result = self._invoke(*args, **kwargs)
        finally:
            HELPER.incr(self._method_name, count=1)
        return result
