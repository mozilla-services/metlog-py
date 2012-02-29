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
    def set_fn(self, fn):
        self._fn = fn
        if self._fn is None:
            return

        if isinstance(fn, MetricsDecorator):
            if hasattr(fn, '_metrics_fn_code'):
                self._metrics_fn_code = fn._metrics_fn_code
            self._method_name = fn._method_name
        else:
            if hasattr(self._fn, 'func_code'):
                self._metrics_fn_code = getattr(self._fn, 'func_code')
            self._method_name = return_fq_name(self._fn)

    def metlog_kw(self, kwargs):
        self.kwargs = kwargs

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
    def __init__(self, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            fn = args[0]
            self.set_fn(fn)
            self.metlog_kw({'name': self._method_name})
        else:
            self.set_fn(None)
            self.metlog_kw(kwargs)

    @rebind_dispatcher('metlog_call', decorator_name='timeit')
    def __call__(self, *args, **kwargs):
        if self._fn is None and callable(args[0]):
            self.set_fn(args[0])
            return self

        return self._invoke(*args, **kwargs)

    def metlog_call(self, *args, **kwargs):
        if self._fn is None and callable(args[0]):
            self.set_fn(args[0])
            return self

        with HELPER.timer(**self.kwargs):
            return self._invoke(*args, **kwargs)


class incr_count(MetricsDecorator):
    """
    Decorate any callable for metrics timing.
    """
    def __init__(self, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            fn = args[0]
            self.set_fn(fn)
            self.metlog_kw({'name': self._method_name, 'count': 1})
        else:
            self.set_fn(None)
            self.metlog_kw(kwargs)


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
            HELPER.incr(**self.kwargs)
        return result
