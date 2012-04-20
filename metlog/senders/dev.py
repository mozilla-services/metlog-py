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
    import simplejson as json
except ImportError:
    import json  # NOQA
import sys


class StreamSender(object):
    """
    Emits messages to a provided stream object.
    """
    def __init__(self, stream, payload_only=True):
        """
        :param stream: Stream object to which the messages should be written.
        :param payload_only: If False then the entire JSON version of each
                             message will be written. If True, only the
                             `payload` value from each message will be written.
        """
        self.stream = stream
        self.payload_only = payload_only

    def send_message(self, msg):
        """Deliver message to the stream object."""
        output = (msg['payload'] if self.payload_only
                  else json.dumps(msg, indent=4))
        self.stream.write('%s\n' % output)
        self.stream.flush()


class StdOutSender(StreamSender):
    """
    Emits metlog messages to stdout.
    """
    def __init__(self, *args, **kwargs):
        super(StdOutSender, self).__init__(sys.stdout, *args, **kwargs)


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
