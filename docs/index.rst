.. metlog-py documentation master file, created by
   sphinx-quickstart on Wed Feb  8 17:50:44 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


metlog-py
=========

metlog-py is a Python library used for inserting messages into the "Metlog"
system for application logging and metrics gathering. The Metlog system is
meant to reduce developer friction with regard to generating and sending data
points intended for a number of different analytics and processing back
ends. It does this by separating the concerns of message generation from those
of message delivery and analysis. The Metlog system consists of three pieces:

generator
  This is the application that will be generating the data that is to be sent
  into the system.

router
  This is the initial recipient of the messages that the generator will be
  sending. Typically, a metlog router deserializes the messages it receives,
  examines them, and decides based on the message metadata or contents which
  endpoint(s) to which the message should be delivered.

endpoints
  Different types of messages lend themselves to different types of
  presentation, processing, and analytics. The router has the ability to
  deliver messages of various types to destinations that are appropriate for
  handling those message types. For example, simple log messages might be
  output to a log file, while counter timer info is delivered to a `statsd
  <https://github.com/etsy/statsd>`_ server, and Python exception information
  is sent to a `Sentry <https://github.com/dcramer/sentry>`_ server.

The metlog-py library you are currently reading about is a client library meant
to be used by Python-based generator applications. It provides a means for
those apps to insert messages into the system for delivery to the router and,
ultimately, one or more endpoints.

There are two primary components to the metlog-py library, the :doc:`api/client`
client class which exposes the primary metlog client API, and the various
:doc:`api/senders` classes, one of which must be provided to the MetlogClient and
which handles the actual delivery of the message to the router component.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

