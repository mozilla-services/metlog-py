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
Callables that provide message filters for the MetlogClient. Each provider
accepts needed filter configuration values, and returns a filter function
usable by a MetlogClient instance.

Each filter accepts a single `msg` dictionary argument and returns a boolean
value: True if a message *should* be delivered, False if a message *should not*
be delivered. Note that the `msg` dictionary *may* be mutated by the filter.
"""


def severity_max_provider(severity):
    """
    Filter if message severity is greater than specified `severity`.
    """
    def severity_max(msg):
        if msg['severity'] > severity:
            return False
        return True

    return severity_max


def type_blacklist_provider(types):
    """
    Filter if message type is in the `types` value.
    """
    def type_blacklist(msg):
        if msg['type'] in types:
            return False
        return True

    return type_blacklist


def type_whitelist_provider(types):
    """
    Filter if message type is NOT in the `types` value.
    """
    def type_whitelist(msg):
        if msg['type'] not in types:
            return False
        return True

    return type_whitelist


def type_severity_max_provider(types):
    """
    Filter if message type has specified maximum severity value and message
    severity is higher than this maximum. Each keyword argument key should be a
    message type name, and each keyword argument value should be the maximum
    allowed severity for that message type.
    """
    for msgtype in types:
        severity_filter = severity_max_provider(**types[msgtype])
        types[msgtype] = severity_filter

    def type_severity_max(msg):
        msgtype = msg['type']
        if msgtype not in types:
            return True
        severity_filter = types[msgtype]
        return severity_filter(msg)

    return type_severity_max
