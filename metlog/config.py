"""
This module provides helpers to handle configuration details as well
as providing some late binding helper objects which can be used to
hook into plugin systems.

"""
from metlog.exceptions import EnvironmentNotFoundError
from metlog.exceptions import UnknownConfigurationType
from textwrap import dedent
import ConfigParser
import StringIO
import os
import re
import types


def Config(blob, ns):
    """
    Parse an INI style text, python dictionary or a ConfigParser object
    """
    if isinstance(blob, basestring):
        return parse_textini(blob, ns)
    elif isinstance(blob, types.DictType):
        return parse_configdict(blob, ns)
    elif isinstance(blob, ConfigParser.ConfigParser):
        return parse_configobj(blob, ns)
    raise UnknownConfigurationType("Configuration type is unrecognized")


def parse_textini(text, ns):
    """
    Parse INI text into a dictionary for use with Metlog
    """
    cfg = ConfigParser.ConfigParser()
    txt = dedent(text)
    cfg.readfp(StringIO.StringIO(txt))
    return parse_configobj(cfg, ns)

def parse_configobj(config_obj, metlog_ns):
    '''
    Given a standard Python ConfigParser object, use the metlog_ns and
    extract all configuration for the Metlog client system.
    '''

    result = {}
    for opt in config_obj.options(metlog_ns):
        result[opt] = convert(config_obj.get(metlog_ns, opt))

    return check_config_dict(result)


def parse_configdict(config_dict, metlog_ns=None):
    '''
    Given a standard dictionary, use the metlog_ns and extract all
    configuration for the Metlog client system.

    If no metlog_ns is provided, assume that we are using the top
    level dictionary.
    '''

    if metlog_ns != None:
        config_dict = config_dict[metlog_ns]

    result = {}
    for opt in config_dict.keys():
        result[opt] = convert(config_dict.get(opt))

    return check_config_dict(result)


####### Internal functions below #######

_IS_NUMBER = re.compile('^-?[0-9].*')
_IS_ENV_VAR = re.compile('\$\{(\w.*)?\}')

def convert(value):
    """Converts a config value"""
    def _get_env(matchobj):
        if not matchobj:
            return
        var = matchobj.groups()[0]
        if var not in os.environ:
            raise EnvironmentNotFoundError(var)
        return os.environ[var]

    def _convert(value):
        if not isinstance(value, basestring):
            # already converted
            return value

        value = value.strip()
        if _IS_NUMBER.match(value):
            try:
                return int(value)
            except ValueError:
                pass
        elif value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        elif value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        match_obj = _IS_ENV_VAR.match(value)
        if match_obj:
            return _get_env(match_obj)
        return value

    if isinstance(value, basestring) and '\n' in value:
        return [line for line in [_convert(line)
                                  for line in value.split('\n')]
                if line != '']

    return _convert(value)


def check_config_dict(cfg_dict):
    """
    Check that we have at a minimum, an enabled flag.  

    If enabled, we should have a 'sender_backend' key defined
    """
    assert cfg_dict.has_key('enabled')

    if cfg_dict['enabled']:
        assert cfg_dict.has_key('sender_backend')

    return cfg_dict
