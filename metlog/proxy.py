# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****
"""
This module provides some decorators around the standard metlog client
to provide richer methods. In essence, logging users can bind
methods to the metlog client at runtime in a safe manner.

The composition of the particular decorators is managed by metlog's
configuration file. Each d
"""

import types


class Proxy(object):
    """
    This is a proxy class which safely allows adding new methods
    around an underlying object
    """
    def __init__(self, subject):
        self._subject = subject
        self._unbound_methods = {}

    def extend_proxy(self, name, method):
        # Extend the proxy with a new method and bind it directly into
        # the proxy
        assert isinstance(method, types.FunctionType)
        if name in dir(self):
            msg = "The name [%s] is already bound into the proxy" % name
            raise SyntaxError(msg)

        self._unbound_methods[name] = method

        meth = types.MethodType(method, self, self.__class__)
        self.__dict__[name] = meth

    def __dir__(self):
        return list(set(self.__dict__.keys() + dir(self._subject)))

    def __getattr__(self, key):
        # Delegate down to the underlying object if the proxy doesn't
        # contain the attribute we need
        return getattr(self._subject, key)


def log_cef(self, name, severity, environ, config, username='none',
            signature=None, **kw):
    """Creates a CEF record, and emit it in syslog or another file.

    Args:
        - name: name to log
        - severity: integer from 0 to 10
        - environ: the WSGI environ object
        - config: configuration dict
        - signature: CEF signature code - defaults to name value
        - username: user name - defaults to 'none'
        - extra keywords: extra keys used in the CEF extension
    """
    from cef import _get_fields, _format_msg, _filter_params
    config = _filter_params('cef', config)
    fields = _get_fields(name, severity, environ, config, username=username,
                        signature=signature, **kw)
    msg = _format_msg(fields, kw)

    self.metlog(type='cef', payload=msg)

    # Return the formatted message
    return msg
