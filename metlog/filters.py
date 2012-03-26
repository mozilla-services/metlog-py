# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
"""
Callables useful as message filters for the MetlogClient. All filters
should accept three arguments:

:param client: MetlogClient instance
:param config: Dictionary containing any necessary filter configuration
               info
:param msg: Message dictionary

All filters should return a boolean value, True if a message *should* be
delivered, False if a message *should not* be delivered. Note that the `msg`
dictionary *may* be mutated by the filter.
"""


def severity_max(client, config, msg):
    """
    Filter if message severity is greater than config's `severity` value.
    """
    if msg['severity'] > config['severity']:
        return False
    return True


def type_blacklist(client, config, msg):
    """
    Filter if message type is in the config's `types` value.
    """
    if msg['type'] in config['types']:
        return False
    return True


def type_whitelist(client, config, msg):
    """
    Filter if message type is NOT in the config's `types` value.
    """
    if msg['type'] not in config['types']:
        return False
    return True


def type_severity_max(client, config, msg):
    """
    Filter if message type has specified maximum severity value and message
    severity is higher than this maximum.
    """
    type_spec = config['types'].get(msg['type'])
    if type_spec is None:
        return True
    return severity_max(client, type_spec, msg)
