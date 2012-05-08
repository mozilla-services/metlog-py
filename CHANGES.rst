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
