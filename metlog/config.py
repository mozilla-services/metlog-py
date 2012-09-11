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
This module provides helpers to handle MetlogClient configuration details.
"""
from metlog.client import MetlogClient
from metlog.exceptions import EnvironmentNotFoundError
from metlog.path import DottedNameResolver
from textwrap import dedent
import ConfigParser
import StringIO
import copy
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


def nest_prefixes(config_dict, prefixes=None, separator="_"):
    """
    Iterates through the `config_dict` keys, looking for any starting w/ one of
    a specific set of prefixes, moving those into a single nested dictionary
    keyed by the prefix value.

    :param config_dict: Dictionary to mutate. Will also be returned.
    :param prefixes: Sequence of prefixes to look for in `config_dict` keys.
    :param separator: String which separates prefix values from the rest of the
                      key.
    """
    if prefixes is None:
        prefixes = ['sender', 'global']
    for prefix in prefixes:
        prefix_dict = {}
        for key in config_dict.keys():
            full_prefix = prefix + separator
            if key.startswith(full_prefix):
                nested_key = key[len(full_prefix):]
                prefix_dict[nested_key] = config_dict[key]
        if prefix_dict:
            if prefix in config_dict:
                config_dict[prefix].update(prefix_dict)
            else:
                config_dict[prefix] = prefix_dict
    return config_dict


def client_from_dict_config(config, client=None, clear_global=False):
    """
    Configure a metlog client, fully configured w/ sender and plugins.

    :param config: Configuration dictionary.
    :param client: MetlogClient instance to configure. If None, one will be
                   created.
    :param clear_global: If True, delete any existing global config on the
                         CLIENT_HOLDER before applying new config.

    The configuration dict supports the following values:

    logger
      Metlog client default logger value.
    severity
      Metlog client default severity value.
    disabled_timers
      Sequence of string tokens identifying timers that are to be deactivated.
    filters
      Sequence of 2-tuples `(filter_provider, config)`. Each `filter_provider`
      is a dotted name referring to a function which, when called and passed
      the associated `config` dict as kwargs, will return a usable MetlogClient
      filter function.
    plugins
      Nested dictionary containing plugin configuration. Keys are the plugin
      names (i.e. the name the method will be given when attached to the
      client). Values are 2-tuples `(plugin_provider, config)`. Each
      `plugin_provider` is a dotted name referring to a function which, when
      called and passed the associated `config`, will return the usable plugin
      method.
    sender
      Nested dictionary containing sender configuration.
    global
      Dictionary to be applied to CLIENT_HOLDER's `global_config` storage.
      New config will overwrite any conflicting values, but will not delete
      other config entries. To delete, calling code should call the function
      with `clear_global` set to True.

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
    # Make a deep copy of the configuration so that subsequent uses of
    # the config won't blow up
    config = nest_prefixes(copy.deepcopy(config))

    sender_config = config.get('sender', {})
    logger = config.get('logger', '')
    severity = config.get('severity', 6)
    disabled_timers = config.get('disabled_timers', [])
    filter_specs = config.get('filters', [])
    plugins_data = config.pop('plugins', {})
    global_conf = config.get('global', {})

    # update global config stored in CLIENT_HOLDER
    from metlog.holder import CLIENT_HOLDER
    if clear_global:
        CLIENT_HOLDER.global_config = {}
    CLIENT_HOLDER.global_config.update(global_conf)

    resolver = DottedNameResolver()

    # instantiate sender
    sender_clsname = sender_config.pop('class')
    sender_cls = resolver.resolve(sender_clsname)
    sender_args = sender_config.pop('args', tuple())
    sender = sender_cls(*sender_args, **sender_config)

    # initialize filters
    filters = [resolver.resolve(dotted_name)(**cfg)
               for (dotted_name, cfg) in filter_specs]

    # instantiate and/or configure client
    if client is None:
        client = MetlogClient(sender, logger, severity, disabled_timers,
                              filters)
    else:
        client.setup(sender, logger, severity, disabled_timers, filters)

    # initialize plugins and attach to client
    for section_name, plugin_spec in plugins_data.items():
        # each plugin spec is a 2-tuple: (dotted_name, cfg)
        plugin_config = plugin_spec[1]
        plugin_override = plugin_config.pop('override', False)
        plugin_fn = resolver.resolve(plugin_spec[0])(plugin_config)
        client.add_method(plugin_fn, plugin_override)

    return client


def dict_from_stream_config(stream, section):
    """
    Parses configuration from a stream and converts it to a dictionary suitable
    for passing to `client_from_dict_config`.

    :param stream: Stream object containing config information.
    :param section: INI file section containing the configuration we care
                    about.
    """
    config = ConfigParser.SafeConfigParser()
    config.readfp(stream)
    client_dict = {}

    # extract main client configuration
    for opt in config.options(section):
        client_dict[opt] = _convert(config.get(section, opt))

    # extract filter config from filter sections
    filters = []
    filter_sections = [n for n in config.sections()
                       if n.startswith('%s_filter' % section)]
    for filter_section in filter_sections:
        filter_config = {}
        for opt in config.options(filter_section):
            if opt == 'provider':
                # must be a dotted name string, don't convert
                dotted_name = config.get(filter_section, opt)
            else:
                filter_config[opt] = _convert(config.get(filter_section, opt))
        filters.append((dotted_name, filter_config))
    client_dict['filters'] = filters

    # extract plugin config from plugin sections
    plugins = {}
    plugin_sections = [n for n in config.sections()
                       if n.startswith("%s_plugin" % section)]
    for plugin_section in plugin_sections:
        plugin_name = plugin_section.replace("%s_plugin_" % section, '')
        plugin_config = {}
        provider = ''
        for opt in config.options(plugin_section):
            if opt == 'provider':
                # must be a dotted name string, don't convert
                provider = config.get(plugin_section, opt)
            else:
                plugin_config[opt] = _convert(config.get(plugin_section, opt))
        plugins[plugin_name] = (provider, plugin_config)
    client_dict['plugins'] = plugins

    client_dict = nest_prefixes(client_dict)
    return client_dict


def client_from_stream_config(stream, section, client=None,
                              clear_global=False):
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
    "extensions_". Any values prefaced by "global_" will be added to the global
    config dictionary.
    """
    client_dict = dict_from_stream_config(stream, section)
    client = client_from_dict_config(client_dict, client)
    return client


def client_from_text_config(text, section, client=None, clear_global=False):
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
