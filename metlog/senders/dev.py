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
try:
    import simplesjson as json
except ImportError:
    import json  # NOQA
import sys


class StdOutSender(object):
    """
    Emits metlog messages to stdout for dev purposes.
    """
    def send_message(self, msg):
        """JSONify and send to stdout."""
        json_msg = json.dumps(msg)
        sys.stdout.write('%s\n' % json_msg)
        sys.stdout.flush()


class DebugCaptureSender(object):
    """
    Capture up to 100 metlog messages in a circular buffer for inspection
    later. This is only for DEBUGGING.  Do not use this for anything except
    development.
    """
    def __init__(self):
        import collections
        self.msgs = collections.deque(maxlen=100)

    def send_message(self, msg):
        """JSONify and append to the circular buffer."""
        json_msg = json.dumps(msg)
        self.msgs.append(json_msg)
