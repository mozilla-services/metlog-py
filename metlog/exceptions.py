# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

from ConfigParser import Error


class EnvironmentNotFoundError(Error):
    """Raised when an environment variable is not found"""

    def __init__(self, varname):
        Error.__init__(self, 'Variable not found %r' % varname)
        self.varname = varname


class MethodNotFoundError(Error):
    """Raised when a method lookup fails"""
    pass
