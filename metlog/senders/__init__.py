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
from metlog.senders.dev import FileSender  # NOQA
from metlog.senders.dev import StdOutSender  # NOQA
from metlog.senders.dev import StreamSender  # NOQA
from metlog.senders.dev import DebugCaptureSender  # NOQA
from metlog.senders.udp import UdpSender  # NOQA


class NoSendSender(object):
    """
    A non-working sender, primarily used as a placeholder between the time a
    MetlogClient is created and a working sender object is provided.
    """
    def send_message(self, msg):
        """
        Raises NotImplementedError.
        """
        raise NotImplementedError
