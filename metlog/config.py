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
"""
This module provides helpers to handle configuration details as well
as providing some late binding helper objects which can be used to
hook into plugin systems.

"""
from metlog.client import MetlogClient
from metlog.exceptions import EnvironmentNotFoundError
from metlog.path import DottedNameResolver
from textwrap import dedent
import ConfigParser
import StringIO
import os
import re

_IS_INTEGER = re.compile('^-?[0-9].*')
_IS_ENV_VAR = re.compile('\$\{(\w.*)?\}')


def _get_env_val(match_obj):
    var = match_obj.groups()[0]
    if var not in os.environ:
        raise EnvironmentNotFoundError(var)
    return os.environ[var]


def _convert(value):
    """Converts a config value. Numeric integer strings are converted to
    integer values.  'True-ish' string values are converted to boolean True,
    'False-ish' to boolean False. Any alphanumeric (plus underscore) value
    enclosed within ${dollar_sign_curly_braces} is assumed to represent an
    environment variable, and will be converted to the corresponding value
    provided by os.environ.
    """
    def do_convert(value):
        if not isinstance(value, basestring):
            # we only convert strings
            return value

        value = value.strip()
        if _IS_INTEGER.match(value):
            try:
                return int(value)
            except ValueError:
                pass
        elif value.lower() in ('true', 't', 'on', 'yes'):
            return True
        elif value.lower() in ('false', 'f', 'off', 'no'):
            return False
        match_obj = _IS_ENV_VAR.match(value)
        if match_obj:
            return _get_env_val(match_obj)
        return value

    if isinstance(value, basestring) and '\n' in value:
        return [line for line in [do_convert(line)
                                  for line in value.split('\n')]
                if line.strip() != '']

    return do_convert(value)


def client_from_dict_config(config, client=None, plugin_param=None):
    """
    Configure a metlog client, fully configured w/ sender and plugins.

    :param config: Configuration dictionary.
    :param client: MetlogClient instance to configure. If None, one will be
                   created.
    :param plugin_param: Configuration dictionary for methods that will be
                         bound into the MetlogClient instance

    The configuration dict supports the following values:

    logger
      Metlog client default logger value.
    severity
      Metlog client default severity value.
    disabled_timers
      Sequence of string tokens identifying timers that are to be deactivated.
    filters
      Sequence of 2-tuples `(callable, config)`, where `callable` is dotted
      notation reference to filter callable and `config` is dictionary config
      to be passed in during each use of the filter.
    sender
      Nested dictionary containing sender configuration.

    All of the configuration values are optional, but failure to include a
    sender may result in a non-functional Metlog client. Any unrecognized keys
    will be ignored.

    Note that any top level config values starting with `sender_` will be added
    to the `sender` config dictionary, overwriting any values that may already
    be set.

    The sender configuration supports the following values:

    class (required)
      Dotted name identifying the sender class to instantiate.
    args
      Sequence of non-keyword args to pass to sender constructor.
    <kwargs>
      All remaining key-value pairs in the sender config dict will be passed as
      keyword arguments to the sender constructor.
    """
    sender_config = config.get('sender', {})
    for key, value in config.items():
        if key.startswith('sender_'):
            sender_config[key[len('sender_'):]] = value
    config['sender'] = sender_config

    logger = config.get('logger', '')
    severity = config.get('severity', 6)
    disabled_timers = config.get('disabled_timers', [])
    resolver = DottedNameResolver()

    filters = [(resolver.resolve(filter_dottedname), filter_config) for
               (filter_dottedname, filter_config) in config.get('filters', [])]

    sender_clsname = sender_config.pop('class')
    sender_cls = resolver.resolve(sender_clsname)
    sender_args = sender_config.pop('args', tuple())
    sender = sender_cls(*sender_args, **sender_config)

    if client is None:
        client = MetlogClient(sender, logger, severity, disabled_timers,
                              filters)
    else:
        client.setup(sender, logger, severity, disabled_timers, filters)

    # Load plugins and pass in config
    if plugin_param != None:
        for plugin_name, plugin_config in plugin_param.items():
            config = plugin_config.pop('plugin.provider')
            plugin = config(plugin_param[plugin_name])
            client.add_method(plugin_name, plugin)

    return client


def _get_filter_config(config, section):
    """
    Extract the various filter configuration sections from the config object
    and return a filters sequence suitable for passing to the client
    constructor.
    """
    return _get_plugin_config(config, section, 'filter')


def _get_plugin_config(config, section, plugin):
    """
    Extract the various plugin configuration sections from the config object
    and return a plugin sequence suitable for passing to the client
    constructor.
    """
    # plugins config
    plugins_prefix = '%s_%s_' % (section, plugin)
    plugin_sections = [s for s in config.sections()
                       if s.startswith(plugins_prefix)]
    plugins = []
    for plugin_section in plugin_sections:
        plugin_config = {}
        for opt in config.options(plugin_section):
            plugin_config[opt] = _convert(config.get(plugin_section, opt))
        plugin_dottedname = plugin_config.pop(plugin)  # 'plugin' key req'd
        plugins.append((plugin_dottedname, plugin_config))
    return plugins


def client_from_stream_config(stream, section, client=None):
    """
    Extract configuration data in INI format from a stream object (e.g. a file
    object) and use it to generate a Metlog client. Config values will be sent
    through the `_convert` function for possible type conversion.

    :param stream: Stream object containing config information.
    :param section: INI file section containing the configuration we care
                    about.
    :param client: MetlogClient instance to configure. If None, one will be
                   created.

    Note that all sender config options should be prefaced by "sender_", e.g.
    "sender_class" should specify the dotted name of the sender class to use.
    Similarly all extension method settings should be prefaced by
    "extensions_".
    """
    config = ConfigParser.SafeConfigParser()
    config.readfp(stream)
    client_dict = {}
    for opt in config.options(section):
        client_dict[opt] = _convert(config.get(section, opt))

    filters = _get_filter_config(config, section)

    if filters:
        client_dict['filters'] = filters

    # Load any plugin configuration
    plugin_sections = [n for n in config.sections()
                       if n.startswith("%s_plugin" % section)]
    plugin_param = {}

    resolver = DottedNameResolver()

    for plugin_section in plugin_sections:
        plugin_name = plugin_section.replace("%s_plugin_" % section, '')
        plugin_dict = {}
        for opt in config.options(plugin_section):
            if opt == 'provider':
                configurator = resolver.resolve(config.get(plugin_section,
                                                           opt))
                plugin_dict['plugin.provider'] = configurator
                continue
            plugin_dict[opt] = _convert(config.get(plugin_section, opt))
        plugin_param[plugin_name] = plugin_dict

    client = client_from_dict_config(client_dict, client, plugin_param)

    return client


def client_from_text_config(text, section, client=None):
    """
    Extract configuration data in INI format from provided text and use it to
    configure a Metlog client. Text is converted to a stream and passed on to
    `client_from_stream_config`.

    :param text: INI text containing config information.
    :param section: INI file section containing the configuration we care
                    about.
    :param client: MetlogClient instance to configure. If None, one will be
                   created.
    """
    stream = StringIO.StringIO(dedent(text))
    return client_from_stream_config(stream, section, client)
