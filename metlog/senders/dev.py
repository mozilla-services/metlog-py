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

from metlog.path import resolve_name


class StreamSender(object):
    """
    Emits messages to a provided stream object.
    """
    def __init__(self, stream, formatter=None):
        """
        :param stream: Stream object to which the messages should be written.
        :param formatter: Optional callable (or dotted name identifier) that
                          accepts a msg dictionary and returns a formatted
                          string to be written to the stream.
        """
        self.stream = stream
        if formatter is None:
            self.formatter = self.default_formatter
        else:
            if not callable(formatter):
                formatter = resolve_name(formatter)
            self.formatter = formatter

    def default_formatter(self, msg):
        """
        Default formatter, just converts the message to 4-space-indented
        JSON.
        """
        return json.dumps(msg, indent=4)

    def send_message(self, msg):
        """Deliver message to the stream object."""
        output = self.formatter(msg)
        self.stream.write('%s\n' % output)
        self.stream.flush()


class StdOutSender(StreamSender):
    """
    Emits metlog messages to stdout.
    """
    def __init__(self, *args, **kwargs):
        super(StdOutSender, self).__init__(sys.stdout, *args, **kwargs)


class FileSender(StreamSender):
    """
    Emits messages to a filesystem file.
    """
    def __init__(self, filepath, *args, **kwargs):
        filestream = open(filepath, 'a')
        super(FileSender, self).__init__(filestream, *args, **kwargs)


class DebugCaptureSender(object):
    """
    Capture up to 100 metlog messages in a circular buffer for inspection
    later. This is only for DEBUGGING.  Do not use this for anything except
    development.
    """
    def __init__(self, **kwargs):
        import collections
        self.msgs = collections.deque(maxlen=100)
        for k, v in kwargs.items():
            # set arbitrary attributes, useful for testing
            setattr(self, k, v)

    def send_message(self, msg):
        """JSONify and append to the circular buffer."""
        json_msg = json.dumps(msg)
        self.msgs.append(json_msg)
