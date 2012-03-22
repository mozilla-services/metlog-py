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
