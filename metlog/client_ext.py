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
