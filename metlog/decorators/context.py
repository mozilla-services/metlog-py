# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

"""
This module includes code to manage 
"""

import functools
from contextlib import contextmanager
import threading
import thread
from metlog.helper import HELPER

def apache_log(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        req = args[0]
        headers = req.headers

        webserv_log = {}

        wheaders = {}

        wheaders['User-Agent'] = headers.get('User-Agent', '')
        wheaders['path'] = getattr(req, 'path', '_no_path_')
        wheaders['host'] = getattr(req, 'host', '_no_host_')

        webserv_log['headers'] = wheaders

        def send_logmsg(tl_data):
            # this stuff gets stuffed into a callback
            # Fetch back any threadlocal variables and
            if has_tlocal():
                webserv_log['threadlocal'] = get_tlocal()
            else:
                webserv_log['threadlocal'] = None
            HELPER.metlog('wsgi', fields=webserv_log)

        result = None

        with thread_context(send_logmsg) as thread_dict:  # NOQA
            result = fn(*args, **kwargs)

        return result

    return wrapper


@contextmanager
def thread_context(callback):
    """
    This context manager accepts a callback which is used to send a metlog
    message.

    The context manager sets up threadlocal storage which the application may
    use to store app specific logging data.  

    Access to the thread local storage is provided by a dictionary yielded
    by the context manager.  
    
    Prior to the context manager exiting, the callback is invoked with a single
    argument - the local storage dictionary. This is used so that metlog can
    bind in any application specific data.

    When the context manager finally terminates, the threadlocal storage is
    garbage collected.
    """

    if not has_tlocal():
        set_tlocal({})

    # This context manager yields a dictionary that is thread local
    # Upon contextblock exit, the dictionary will be passed into the
    # callback function and finally garbage collected
    yield get_tlocal()

    try:
        callback(get_tlocal())
    finally:
        clear_tlocal()


_LOCAL_STORAGE = threading.local()
_RLOCK = threading.RLock()


def has_tlocal():
    result = None
    with _RLOCK:
        thread_id = str(thread.get_ident())
        result = hasattr(_LOCAL_STORAGE, thread_id)
    return result


def set_tlocal(value):
    with _RLOCK:
        thread_id = str(thread.get_ident())
        setattr(_LOCAL_STORAGE, thread_id, value)


def clear_tlocal():
    with _RLOCK:
        thread_id = str(thread.get_ident())
        if hasattr(_LOCAL_STORAGE, thread_id):
            delattr(_LOCAL_STORAGE, thread_id)


def get_tlocal():
    """
    Create thread local storage if none exists yet and 
    """
    # TODO: this should really take in a namespace so that we can have different
    # loggers use thread local storage.  Will also need to have some kind of
    # reference count to make sure we dont' garbage collect too early.
    result = None
    with _RLOCK:
        thread_id = str(thread.get_ident())
        if not has_tlocal():
            set_tlocal({})
        result = getattr(_LOCAL_STORAGE, thread_id)
    return result


