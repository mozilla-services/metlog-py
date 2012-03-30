Metlog Configuration
--------------------

To assist with getting a working Metlog set up, metlog-py provides a
:doc:`api/config` module which will take declarative configuration info in
either ini file or python dictionary format and use it to configure a
MetlogClient instance. Even if you choose not to use these configuration
helpers, this document provides a good overview of the configurable options
provided by default by the :doc:`api/client` client class.

The config module will accept configuration data either in ini format (as a
text value or a stream input) or as a Python dictionary value. This document
will first describe the supported ini file format, followed by the
corresponding dictionary format to which the ini format is ultimately
converted behind the scenes.

ini format
==========

The primary `MetlogClient` configuration should be provided in a `metlog`
section of the provided ini file text. (Note that the actual name of the
section is passed in to the config parsing function, so it can be any legal ini
file section name, but for illustration purposes these documents will assume
that the section name is `metlog`.) A sample `metlog` section might look like
this::

  [metlog]
  logger = myapp
  severity = 4
  disabled_timers = foo
                    bar
  sender_class = metlog.senders.zmq.ZmqPubSender
  sender_bindstrs = tcp://127.0.0.1:5565
  sender_queue_length = 5000

Of all of these settings, only `sender_class` is strictly required. A detailed
description of each option follows:

logger
  Each metlog message that goes out contains a `logger` value, which is simply
  a string token meant to identify the source of the message, usually the
  name of the application that is running. This can be specified separately for
  each message that is sent, but the client supports a default value which will
  be used for all messages that don't explicitly override. The `logger` config
  option specifies this default value. This value isn't strictly required, but
  if it is omitted '' (i.e. the empty string) will be used, so it is strongly
  suggested that a value be set.

severity
  Similarly, each metlog message specifies a `severity` value corresponding to
  the integer severity values defined by `RFC 3164
  <https://www.ietf.org/rfc/rfc3164.txt>`_. And, again, while each message can
  set its own severity value, if one is omitted the client's default value will
  be used. If no default is specified here, the default default (how meta!)
  will be 6, "Informational".

disabled_timers
  Metlog natively supports "timer" behavior, which will calculate the amount of
  elapsed time taken by an operation and send that data along as a message to
  the back end. Each timer has a string token identifier. Because the act of
  calculating code performance actually impacts code performance, it is
  sometimes desirable to be able to activate and deactivate timers on a case by
  case basis. The `disabled_timers` value specifies a set of timer ids for
  which the client should NOT actually generate messages. Metlog will attempt
  to minimize the run-time impact of disabled timers, so the price paid for
  having deactivated timers will be very small. Note that the various timer ids
  should be newline separated.

sender_class
  This should be a Python dotted notation reference to a class (or factory
  function) for a Metlog "sender" object. A sender needs to provide a
  `send_message(msg)` method, which is responsible for serializing the message
  and passing it along to the router / back end / output mechanism /
  etc. metlog-py provides some development senders, but the main one it
  provides for intended production use makes use of ZeroMQ (using the pub/sub
  pattern) to broadcast the messages to any configured listeners.

sender_*
  As you might guess, different types of senders can require different
  configuration values. Any config options other than `sender_class` that start
  with `sender_` will be passed to the sender factory as keyword arguments,
  where the argument name is the option name minus the `sender_` component and
  the value is the specified value. In the example above, the ZeroMQ bind
  string and the queue length will be passed to the ZmqPubSender constructor.

In addition to the main `metlog` section, any other config sections that start
with `metlog_` (or whatever section name is specified) will be considered to be
related to the metlog installation. Only specific variations of these are
supported, however. The first of these is configuration for MetlogClient
:doc:`api/filters`. Here is an example of such a configuration::

  [metlog_filter_sev_max]
  filter = metlog.filters.severity_max
  severity = 4

  [metlog_filter_type_whitelist]
  filter = metlog.filters.type_whitelist
  types = timer
          oldstyle

Each `metlog_filter_*` section must contain a `filter` entry, which is a dotted
name specifying a filter function that will be added to the MetlogClient's
filters. The rest of the options in that section will be converted into a
config dictionary which will be passed in to each invocation of the filter
function. The filters will be applied in the order they are specified. In this
case a "severity max" filter will be applied, so that only messages with a
severity of 4 (i.e. "warning") or lower will actually be passed in to the
sender. Additionally a "type whitelist" will be applied, so that only messages
of type "timer" and "oldstyle" will be delivered.


plugins
=======

Metlog allows you to bind new extensions onto the client through a
plugin mechanism.

Each plugin must have a configuration section name with a prefix of 
`metlog_plugin_`.  Configuration is parsed into a dictionary, passed
into a configurator and then the resulting plugin method is bound 
to the client.

Each configuration section for a plugin must contain at least one
option with the name `provider`. This is a dotted name for a function
which will be used to configure a plugin.  The return value for the
provider is a configured method which will then be bound into the
Metlog client.

Each plugin extension method is bound in with the suffix that follows
the `metlog_plugin_` prefix in the configuration section name.

An example best demonstrates what can be expected.  To load the dummy
plugin, you need a `metlog_plugin_dummy` section as well as some
configuration parameters. Here's an example ::

    [metlog_plugin_dummy]
    provider=metlog.tests.plugin:config_plugin
    port=8080
    host=localhost

Once you obtain a reference to a client, you can access the new
method. ::

    from metlog.decorators.base import CLIENT_WRAPPER
    client = CLIENT_WRAPPER.client
    client.dummy('some', 'ignored', 'arguments', 42)


dictionary format
=================

When using the `client_from_text_config` or `client_from_stream_config`
functions of the config module to parse an ini format configuration, metlog-py
simply converts these values to a dictionary which is then passed to
`client_from_dict_config`. If you choose to not use the specified ini format,
you can parse configuration yourself and call `client_from_dict_config`
directly. The configuration specified in the "ini format" section above would
be converted to the following dictionary::

  {'logger': 'myapp',
   'severity': 4,
   'disabled_timers': ['foo', 'bar'],
   'sender': {'class': 'metlog.senders.zmq.ZmqPubSender',
              'bindstrs': 'tcp://127.0.0.1:5565',
              'queue_length': 5000,
              },
   'filters': [('metlog.filters.severity_max',
                {'severity': 4},
                ),
               ('metlog.filters.type_whitelist',
                {'types': ['timer', 'oldstyle']},
                ),
               ],
   }

To manually load a Metlog client with plugins, the
`client_from_dict_config` function allows you to pass in a plugin_parm
argument.  The configuration specified in the "plugins" section above
would be converted into the following dictionary ::

    {'dummy': {'plugin.provider': 'metlog.tests.plugin:config_plugin',
               'port': 8080,
               'host': 'localhost'
              }
    }



