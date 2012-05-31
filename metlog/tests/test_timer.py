# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from metlog.client import _Timer, MetlogClient
from mock import Mock
from nose.tools import assert_raises, eq_, ok_

import threading
import time


timer_name = 'test'


def _make_em():
    mock_client = Mock(spec=MetlogClient)
    timer = _Timer(mock_client, timer_name, {})
    return mock_client, timer


def test_only_decorate_functions():
    mock_client, timer = _make_em()

    def bad_timer_arg():
        timer('foo')
    assert_raises(ValueError, bad_timer_arg)


def test_contextmanager():
    mock_client, timer = _make_em()
    with timer as timer:
        time.sleep(0.01)

    eq_(mock_client.timer_send.call_count, 1)
    timing_args = mock_client.timer_send.call_args[0]
    eq_(timing_args[0], timer_name)
    ok_(timing_args[1] >= 10)
    eq_(timing_args[1], timer.result)


def test_decorator():
    mock_client, timer = _make_em()

    @timer
    def timed():
        time.sleep(0.01)

    timed()
    eq_(mock_client.timer_send.call_count, 1)
    timing_args = mock_client.timer_send.call_args[0]
    eq_(timing_args[0], timer_name)
    ok_(timing_args[1] >= 10)


def test_attrs_threadsafe():
    mock_client, timer = _make_em()

    def reentrant(val):
        sentinel = object()
        if getattr(timer, 'value', sentinel) is not sentinel:
            ok_(False, "timer.value already exists in new thread")
        timer.value = val

    t0 = threading.Thread(target=reentrant, args=(10,))
    t1 = threading.Thread(target=reentrant, args=(100,))
    t0.start()
    time.sleep(0.01)  # give it enough time to be sure timer.value is set
    t1.start()  # this will raise assertion error if timer.value from other
                # thread leaks through
