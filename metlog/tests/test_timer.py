from metlog.client import _Timer, MetlogClient
from mock import Mock
from nose.tools import eq_, ok_

import threading
import time


def _make_em():
    mock_client = Mock(spec=MetlogClient)
    timer = _Timer(mock_client)
    return mock_client, timer


def test_contextmanager():
    mock_client, timer = _make_em()
    with timer as result:
        time.sleep(0.01)

    eq_(mock_client.timing.call_count, 1)
    timing_args = mock_client.timing.call_args[0]
    eq_(timing_args[0], timer)
    ok_(timing_args[1] >= 10)
    eq_(timing_args[1], result.ms)


def test_decorator():
    mock_client, timer = _make_em()

    def timed():
        time.sleep(0.01)

    timer(timed)()
    eq_(mock_client.timing.call_count, 1)
    timing_args = mock_client.timing.call_args[0]
    eq_(timing_args[0], timer)
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
