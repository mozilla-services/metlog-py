0.9.9 - ????-??-??
==================

0.9.8 - 2012-10-05
==================

- MetlogClient now accepts single string values for the `disabled_timers`
  argument.
- Fixed bug where timer wouldn't be disabled if the function name didn't match
  the timer name.
- Added better error handling for invalid unicode. Unserializable
  messages will now get routed to stderr
- A new metlog benchmark command line utility (mb) is now included


0.9.7 - 2012-09-11
==================

- Fixed a bug where `client_from_dict_config` would mutate the input
  configuration causing subsequent use of the configuration to fail.

0.9.6 - 2012-09-11
==================

- Couple of bug fixed in decorator base class.
- Added support for UdpSender to have multiple listener hosts.


0.9.5 - 2012-08-14
==================

- Properly handle 'self' arguments when decorators are used on a method.
- Only apply string formatting to 'oldstyle' messages if string formatting args
  are actually provided.

0.9.4 - 2012-07-25
==================

- Added a testcase against the UDP input plugin.
- Fixed bug in socket.sendto function signature.

0.9.3 - 2012-07-18
==================

- MetlogClient's `override` argument now accepts method name to override
  instead of `True`.
- Decorator tests now get the expected envelope version from the module source
  code rather than hard coded in the tests.
- Added udp sender.

0.9.2 - 2012-06-22
==================

- Plugin method names are now expected to be stored in the `metlog_name`
  attribute of the provided function rather than passed in separately.
- 'oldstyle' messages now support string substitution using provided args and
  the `exc_info` keyword argument for slightly better stdlib logging
  compatibility.
- ZeroMQ sender now uses gevent safe implementations of `Queue` class and `zmq`
  module if the gevent monkeypatches have been applied.

0.9.1 - 2012-06-08
==================

- Added `StdLibLoggingSender` that delegates message delivery to Python's
  standard library `logging` module.

0.9 - 2012-05-31
================

- Refactored / simplified filter and plug-in config loading code
- Filter functions now use closures for filter config (matching plug-in config)
  instead of passing the config as an argument each time.
- `MetlogClient.add_method` now supports `override` argument to force the issue
  of replacing existing attributes.
- Added `metlog_hostname` and `metlog_pid` to the message envelope handed to the
  sender.
- Added support for `rate` argument to `MetlogClient.incr` method.
- `MetlogClient.timer` converted from a property to a method, allowing for much
  better performance and much simpler code.
- Got rid of `new_default` argument `MetlogClientHolder.delete_client`. Folks
  can set a new default w/ another function call if necessary.
- `DebugCaptureSender.__init__` now accepts arbitrary keyword args and stores
  them as attributes on the instance to allow for easier testing of the config
  parsing code.

0.8.5 - 2012-05-07
==================

- Replaced `metlog.decorators.base.MetlogClientWrapper` with
  `metlog.holder.MetlogClientHolder` which is a bit more useful and a bit more
  sane.
- Moved Python stdlib `logging` compatibility hooks into its own module.
- Updated config parsing to support global values stored in the CLIENT_HOLDER.
- Added `is_active` property to `MetlogClient`.
- Heavily revised "Getting Started" documentation.
- Added `dict_from_stream_config` function to `config`.
- Extracted `StreamSender` from `StdOutServer`, added support for arbitrary
  formatters for the output.
- Added `ZmqHandshakePubSender` which communicates w/ clients via a control
  channel.
- ZMQ senders now use connection pooling.

0.8.4 - 2012-04-18
==================

- "Getting started" documentation
- Overall documentation ToC
- Added Metlog stdlib logging handler so logging in dependency libraries can be
  routed to Metlog
- Use 0mq connection pool instead of creating a new 0mq connection for each new
  thread
- Initial implementation of 0mq "Handshaking Client" which will use a separate
  control channel to establish communication with 0mq subscribers.
- Added `debug_stderr` flag to ZmqPubSender which will also send all output to
  stderr for capturing output when error messages aren't getting through to the
  Metlog listener.

0.8.3 - 2012-04-05
==================

- Added support for simple message filtering directly in the metlog client
- "Metlog Configuration" documentation
- Added support for setting up client extension methods from configuration

0.8.2 - 2012-03-22
==================

- Added `config`, `decorators`, and `exceptions` to sphinx API docs
- Support for passing a client in to the `client_from_*` functions
  to reconfigure an existing client instead of creating a new one
- Docstring / documentation improvements
- Added `reset` method to `MetlogClientWrapper`
- Add support for keeping track of applied decorators to `MetlogDecorator`
  class
- Added `NoSendSender` class for use when a client is create w/o a sender

0.8.1 - 2012-03-01
==================

- Support for specific timers to be disabled
- Support for dynamic extension methods to be added to MetlogClient
- "Classic" logger style API added to MetlogClient
- Helper code added to create client and sender from configuration data
- Support for "deferred" decorators that don't actually bind to the wrapped
  function until after Metlog configuration can be loaded
- `timeit` and `incr_count` deferred decorators provided
- Stole most of `pyramid.path`
- README file is now used as package `long_description` value

0.8 - 2012-02-13
================

- Initial release
