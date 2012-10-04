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
from metlog.decorators.base import MetlogDecorator


class timeit(MetlogDecorator):
    """
    Lazily decorate any callable with a metlog timer.
    """
    def predicate(self):
        client = self.client
        timer_name = self.args[0] if self.args else self._fn.__name__
        if (timer_name in client._disabled_timers or
            '*' in client._disabled_timers):
            return False
        return super(timeit, self).predicate()

    def metlog_call(self, *args, **kwargs):
        if self.args is None:
            self.args = tuple()
        if self.kwargs is None:
            self.kwargs = {'name': self._fn_fq_name}
        with self.client.timer(*self.args, **self.kwargs):
            return self._fn(*args, **kwargs)


class incr_count(MetlogDecorator):
    """
    Lazily decorate any callable w/ a wrapper that will increment a metlog
    counter whenever the callable is invoked.
    """
    def metlog_call(self, *args, **kwargs):
        if self.args is None:
            self.args = tuple()
        if self.kwargs is None:
            self.kwargs = {'name': self._fn_fq_name, 'count': 1}
        try:
            result = self._fn(*args, **kwargs)
        finally:
            self.client.incr(*self.args, **self.kwargs)
        return result
