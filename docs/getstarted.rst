Getting Started
===============

There are two primary components with which users of the metlog-py library
should be aware. The first is the :doc:`api/client` client class. The
MetlogClient exposes the main Metlog API, and is generally your main point of
interaction with the Metlog system. The client doesn't do very much, however;
it just provides convenience methods for constructing messages of various types
and then passes the messages along. Actual message delivery is handled by a
:doc:`sender <api/senders>`. Without a properly configured sender, a
MetlogClient is useless.

The first question you're likely to ask when using metlog-py, then, will
probably be "How the heck do I get my hands on a properly configured client /
sender pair?" You could read the source and instantiate and configure these
objects yourself, but for your convenience we've provided a :doc:`config`
module that simplifies this process considerably. The config module provides
utility functions that allow you pass in a declarative representation of the
settings you'd like for your client and sender objects, and it will create and
configure them for you based on the provided specifications. Some examples of
how this might work are below.

Example 1: Testing
------------------

In this example we're going to pretend we're setting up a Metlog client rig for
use in a testing environment, where configuration is specified directly in
Python code and messages won't actually be delivered to an external destination
but will instead be stored in a debug buffer where they can be accessed
programmatically for test assertions if necessary. The relevant code might look
like this::

    from metlog.config import client_from_dict_config
    from my_framework import get_application_object
    from nose.tools import eq_
    import json


    class MyTestCase(object):

        metlog_config = {
            'logger': 'test',
            'sender': {'class': 'metlog.senders.dev.DebugCaptureSender'},
            }

        marker = object()

        def setUp(self):
            self.app = app = get_application_object()
            self.orig_metlog = getattr(app, self.marker)
            self.metlog = client_from_dict_config(self.metlog_config)
            app.metlog = self.metlog

        def tearDown(self):
            if self.orig_metlog is self.marker:
                del self.app.metlog
            else:
                self.app.metlog = self.orig_metlog

        def test_something(self):
            from my_app import do_something
            do_something()
            msgs = self.metlog.sender.msgs
            eq_(len(msgs), 2)
            first = json.loads(msgs[1])
            eq_(first['payload'], 'expected first payload')
            second = json.loads(msgs[0])
            eq_(second['payload'], 'expected second payload')


Ignore, for now, the hand-wavey reliance on a magical `get_application_object`
utility function. The point is that there's a standard place to put the metlog
client object that will be used by the application code. (Some people like to
put shared resources like this in module scope somewhere, using import to fetch
the object when necessary, but we think this is generally A Bad Idea® so we
don't do so in our examples.)

More important is the `metlog_config` dictionary that defines the metlog
client's configuration (including which sender class to use) and the
`client_from_dict_config` call that creates and returns the configured client
and sender. The sender is a `DebugCaptureSender`, which simply serializes the
messages into JSON and stores them in a circular buffer, very useful for
testing and debugging purposes.


Example 2: Production
---------------------

For the actual production application, we want to get our configuration info
from an ini file, and we'll want to use the `ZmqPubSender` to send the messages
out to a Metlog routing app using a ZeroMQ pub-sub socket. The configuration
file would have the following section::

    [metlog]
    logger = myapp
    sender_class = metlog.senders.zmq.ZmqPubSender
    sender_bindstrs = tcp:10.10.10.10:5655
    sender_queue_length = 5000

Then somewhere in your application's initialization code you might have the
following snippet::

    from metlog.config import client_from_stream_config
    from my_framwork import get_application_object

    def called_during_initialization():
        app = get_application_object()
        with open('/path/to/file.ini') as inifile:
            app.metlog = client_from_stream_config(inifile, 'metlog')

And then elsewhere in your code you can use the client::

    def do_something():
        app.metlog.info('expected first payload')
        for i in range(20):
            print i
        app.metlog.info('expected second payload')

