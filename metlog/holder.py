# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from metlog.client import MetlogClient
from metlog.config import client_from_dict_config
import threading


class MetlogClientHolder(object):
    """
    This is meant to be used as a singleton class that will hold references to
    MetlogClient instances and any required process-wide config data.
    """
    def __init__(self):
        self._clients = dict()
        self.global_config = dict()
        self.lock = threading.Lock()  # write lock for adding clients

    def get_client(self, name):
        """
        Return the specified MetlogClient, creating it if it doesn't exist.
        *NOTE*: Auto-created MetlogClient instances will *not* yet be usable,
        it is the downstream developer's responsibility to provide them with a
        working sender.

        :param name: String token identifying the client, also used as the
                     client's `logger` value.
        """
        client = self._clients.get(name)
        if client is None:
            with self.lock:
                # check again to make sure nobody else got the lock first
                client = self._clients.get(name)
                if client is None:
                    # TODO: there is no sender set here - grab one
                    # based on the globalconfig
                    client = MetlogClient(sender=None, logger=name)
                    if (not self._clients
                        and not self.global_config.get('default')):
                        # first one, set as default
                        self.global_config['default'] = name
                    self._clients[name] = client
        return client

    def set_client(self, name, client):
        """
        Provides a way to add a pre-existing MetlogClient to the ones stored
        in the holder.
        """
        with self.lock:
            self._clients[name] = client
            if len(self._clients) == 1:
                # first one, set as default
                self.global_config['default'] = name

    def set_default_client_name(self, name):
        """
        Convenience method for specifying what should be the default client.
        """
        self.global_config['default'] = name

    @property
    def default_client(self):
        """
        Return the default MetlogClient (as specified by the `default` value in
        the global_config dict).
        """
        default_name = self.global_config.get('default')
        if default_name is None:
            return
        return self._clients.get(default_name)

    def delete_client(self, name):
        """
        Deletes the specified client from the set of stored clients.

        :param name: Name of the client object to delete.
        """
        if name in self._clients:
            del self._clients[name]
        if self.global_config['default'] == name:
            del self.global_config['default']


CLIENT_HOLDER = MetlogClientHolder()


def get_client(name, config_dict=None):
    """
    Return client of the specified name from the CLIENT_HOLDER.

    :param name: String token to identify the MetlogClient, also used for the
                 default `logger` value of that client. `ValueError` will be
                 raised if a config is provided w/ a different `logger` value.
    :param config_dict: Configuration dictionary to be applied to the fetched
                        client.
    """
    client = CLIENT_HOLDER.get_client(name)
    if config_dict:
        logger = config_dict.get('logger')
        if logger and logger != name:
            raise ValueError('Config `logger` value must either match `name` '
                             'argument or be left blank.')
        if not logger:
            config_dict['logger'] = name
        client = client_from_dict_config(config_dict, client=client)
    return client
