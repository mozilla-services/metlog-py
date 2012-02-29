from metlog.decorators.context import clear_tlocal
from metlog.decorators.context import get_tlocal
from metlog.decorators.context import has_tlocal
from metlog.decorators.context import set_tlocal
from metlog.decorators.context import thread_context

import unittest

class TestThreadLocal(unittest.TestCase):
    def setUp(self):
        if has_tlocal():
            clear_tlocal()

    def test_set_tlocal(self):
        assert not has_tlocal()
        set_tlocal({'foo': 432432})
        value = get_tlocal()
        assert value['foo'] == 432432

    def test_threadlocal(self):
        assert not has_tlocal()
        tmp = get_tlocal()
        assert tmp == {}
        tmp['foo'] = 42

        callback_invoked = {'result': False}

        def cb(data):
            assert len(tmp_2) == 2
            assert tmp_2['bar'] == 43
            callback_invoked['result'] = True

        with thread_context(cb) as tmp_2:
            assert len(tmp_2) == 1
            assert tmp_2['foo'] == 42
            tmp_2['bar'] = 43

        assert callback_invoked['result']

        # The thead context should have cleaned up the
        assert not has_tlocal()

    def test_new_context(self):
        """
        Check that a thread_context context manager will automaticaly
        create the dictionary storage for thread local data
        """
        context_worked = {'result': False}

        def callback(data):
            assert data['foo'] == 'bar'
            context_worked['result'] = True

        with thread_context(callback) as data:
            assert len(data) == 0
            data['foo'] = 'bar'

        assert context_worked['result']
        assert not has_tlocal()
