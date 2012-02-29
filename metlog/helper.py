# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

from metlog.client import MetlogClient
from metlog.path import resolve_name

class MetlogHelper(object):
    """
    This is class acts as a lazy proxy to the MetlogClient.

    We need this to provide late binding of the MetlogClient so that decorators
    which use Metlog have a chance to be configured prior to affecting the
    callable which is being decorated
    """
    def __init__(self):
        self._reset()

        # Track any disabled loggers
        self._disabled = {}

        self.set_client(None)

    def configure(self, config_dict):
        """
        This method needs to be called to configure the MetlogHelper instance.

        Keys used in the config_dict:

            sender_backend : This is class name of the sender class.  

            All other keys prefixed with 'sender_' are passed to the constructor
            of sender_backend using keyword arguments

            disable_* : Key prefix of 'disable_' is stripped.  The remaining
            name is used as a lookup against functions which have been decorated
            with the 'rebind_dispatcher' decorator. Any matched decorators are
            disabled.
        """
        self.set_client(None)

        # Disable metlog by default
        if not config_dict.get('enabled', False):
            return

        self.set_client(MetlogClient(None))

        # Strip out the keys prefixed with 'sender_'
        sender_keys = dict([(k.replace("sender_", ''), v) \
                        for (k, v) in config_dict.items() \
                        if k.startswith('sender_')])

        klass = resolve_name(sender_keys['backend'])
        del sender_keys['backend']

        disabled_loggers = dict([(k.replace("disable_", ''), v) \
                        for (k, v) in config_dict.items() \
                        if (k.startswith('disable_') and v)])
        self._disabled.update(disabled_loggers)

        self._client.sender = klass(**sender_keys)

        return self


    def is_disabled(self, name):
        # Check if this particular logger is disabled
        return name in self._disabled

    def _reset(self):
        """ Reset the MetlogClientHelper to it's initial state"""
        self._client = None
        self._registry = {}
        self._web_dispatcher = None

    def set_client(self, client):
        """ set the metlog client on the helper """
        if client is None:
            self._reset()
            return

        self._client = client

    def metlog(self, *args, **kwargs):
        return self._client.metlog(*args, **kwargs)

    def timer(self, *args, **kwargs):
        return self._client.timer(*args, **kwargs)

    def incr(self, *args, **kwargs):
        return self._client.incr(*args, **kwargs)


# This is a shared MetlogHelper instance
HELPER = MetlogHelper()
