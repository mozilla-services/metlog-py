# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****

"""
This is a sample plugin for the metlog clien

You can find an entrypoint to it in the metlog-py setup.py file in the
entry_points section.

Each plugin is bound into the metlog client if and only if there is
configuration for the plugin.
"""
METLOG_PLUGIN_NAME = 'dummy'

import copy


class CallableMethod(object):
    def __init__(self, default_verbose, config_dict):
        self._default_verbose = config_dict.pop('verbose', False)
        self._mycopy = copy.deepcopy(config_dict)

    def __call__(self, *args, **kwargs):
        # Most real plugin methods will use the variables captured in the
        # config_dict to override arguments passed in by the developer through
        # *args and **kwargs.  This allows operations to disable specific
        # features of metlog without having to deploy new code.

        self._args = args
        self._kwargs = args
        return self._mycopy


def config_plugin(config_dict):
    # Normally, the config_dict is unwrapped to get
    # some variables that can be used in the closure
    # to disable features
    default_verbose = config_dict.pop('verbose', False)
    my_plugin = CallableMethod(default_verbose, config_dict)
    my_plugin.metlog_name = METLOG_PLUGIN_NAME

    return my_plugin
