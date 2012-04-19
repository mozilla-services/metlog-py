# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contributor(s):
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****


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
        name = "%s.%s.%s" % (klass.__module__, \
                             klass.__name__, \
                             'PyCallable')
    elif func_name:
        # This is some kind of function
        # Note that we can't determine the containing class
        # because return_fq_name is usually called by a decorator
        # and that means the function is not yet bound to an object
        # instance yet
        # Just grab the containing module and the function name
        name = "%s.%s" % (func_module, func_name)
    else:
        # This shouldn't happen, but we don't really want to throw
        # errors just because we can't get some fake arbitrary
        # name for an object
        name = str(func)
        if name.startswith('<') and name.endswith('>'):
            name = name[1:-1]
    return name
