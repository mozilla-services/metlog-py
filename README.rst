=========
metlog-py
=========

metlog-py is a Python client for the "Metlog" system of application logging and
metrics gathering developed by the `Mozilla Services
<https://wiki.mozilla.org/Services>`_ team. The Metlog system is meant to make
life easier for application developers with regard to generating and sending
logging and analytics data to various destinations. It achieves this goal (we
hope!) by separating the concerns of message generation from those of message
delivery and analysis. Front end application code no longer has to deal
directly with separate back end client libraries, or even know what back end
data storage and processing tools are in use. Instead, a message is labeled
with a type (and possibly other metadata) and handed to the Metlog system,
which then handles ultimate message delivery.

The Metlog system consists of three pieces:

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

More information about how Mozilla Services is using Metlog (including what is
being used for a router and what endpoints are in use / planning to be used)
can be found on the relevant `spec page
<https://wiki.mozilla.org/Services/Sagrada/Metlog>`_.
