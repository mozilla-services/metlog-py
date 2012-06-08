# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
"""
Compatibility layer that allows metlog code to generate output using Python's
standard library's `logging` module.
"""
from __future__ import absolute_import
from metlog.client import SEVERITY
import logging
try:
    import simplesjson as json
except ImportError:
    import json  # NOQA

# maps metlog message 'severity' to logging message 'level'
SEVERITY_MAP = {
    SEVERITY.EMERGENCY: logging.CRITICAL,
    SEVERITY.ALERT: logging.CRITICAL,
    SEVERITY.CRITICAL: logging.CRITICAL,
    SEVERITY.ERROR: logging.ERROR,
    SEVERITY.WARNING: logging.WARN,
    SEVERITY.NOTICE: logging.INFO,
    SEVERITY.INFORMATIONAL: logging.INFO,
    SEVERITY.DEBUG: logging.DEBUG,
    }


class StdLibLoggingSender(object):
    """
    Sender that passes messages off to Python stdlib's `logging` module for
    delivery. Messages will be handled one of three ways:

    1. Message payload extracted and sent on as plain text.
    2. Message serialized to JSON and sent on in its entirety.
    3. Message dropped.

    Sender is configurable to allow specification of which message types should
    be handled in which manner.
    """
    def __init__(self, logger_name=None, payload_types=None, json_types=None):
        """
        :param logger_name: Name of logger that should be fetched from logging
                            module.
        :param payload_types: Sequence of message types that should have their
                              payloads extracted and sent on as text.
        :param json_types: Sequence of message types that should be serialized
                           to JSON and sent on.
        """
        if logger_name is None:
            self.logger = logging.getLogger()
        else:
            self.logger = logging.getLogger(logger_name)
        if payload_types is None:
            payload_types = ['oldstyle']
        if isinstance(payload_types, basestring):
            payload_types = [payload_types]
        self.payload_types = set(payload_types)
        if json_types is None:
            json_types = ['*']
        if isinstance(json_types, basestring):
            json_types = [json_types]
        self.json_types = set(json_types)

    def send_message(self, msg):
        if msg['type'] in self.payload_types or '*' in self.payload_types:
            logging_msg = msg['payload']
        elif msg['type'] in self.json_types or '*' in self.json_types:
            logging_msg = json.dumps(msg)
        else:
            # drop it
            return
        lvl = SEVERITY_MAP.get(msg['severity'], logging.WARN)
        self.logger.log(lvl, logging_msg)
