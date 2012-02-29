# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

import functools
from metlog.helper import HELPER
from metlog.exceptions import MethodNotFoundError

def rebind_dispatcher(method_name, decorator_name=None):
    """
    This decorator can only be used on methods of a class.  The intent is to
    conditionally rebind an alternate method in place of the decorated method if
    metlog is enabled for the decorated method.
    """
    def wrapped(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            
            # This is a reference the class of the decorators.
            # ie: incr_count or timeit
            klass = args[0].__class__

            if not HELPER._client:
                # No Metlog client is bound in, metlog must be disabled.
                #
                # Get rid of the decorator behavior by binding the callable 
                # into the decorator object instance so that getattr
                setattr(klass, func.__name__, func)
                return func(*args, **kwargs)
            elif HELPER.is_disabled(decorator_name):
                # Metlog is disabled on all decorators with this name
                #
                # Get rid of the decorator
                setattr(klass, func.__name__, func)
                return func(*args, **kwargs)
            else:
                # Metlog is enabled for this method - go and rebind the
                # alternate method inplace over the current method
                new_method = getattr(klass, method_name, None)
                if not new_method:
                    msg = 'No such method: [%s]' % method_name
                    raise MethodNotFoundError(msg)
                setattr(klass, func.__name__, new_method)
                return new_method(*args, **kwargs)
        return inner
    return wrapped


def return_fq_name(func, klass=None):
    """
    Resolve a fully qualified name for a function
    or method
    """
    # Forget checking the type via isinstance, just check for anything
    # that looks like it might be useful in constructing a usable name

    func_name = getattr(func, 'func_name', None)
    func_module = getattr(func, '__module__', None)

    if klass:
        name = "%s:%s.%s" % (klass.__module__, \
                             klass.__name__, \
                             'PyCallable')
    elif func_name:
        # This is some kind of function
        # Note that we can't determine the containing class
        # because return_fq_name is usually called by a decorator
        # and that means the function is not yet bound to an object
        # instance yet
        # Just grab the containing module and the function name
        name = "%s:%s" % (func_module, func_name)
    else:
        # This shouldn't happen, but we don't really want to throw
        # errors just because we can't get some fake arbitrary
        # name for an object
        name = str(func)
        if name.startswith('<') and name.endswith('>'):
            name = name[1:-1]
    return name
