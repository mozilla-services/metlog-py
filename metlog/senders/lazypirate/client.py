# Lazy Pirate client
# Use zmq_poll to do a safe request-reply
# To run, start lpserver and then randomly kill/restart it
#
# Author: Daniel Lundin <dln(at)eintr(dot)org>
#

import time
import threading
import sys

try:
    if 'gevent.monkey' in sys.modules:
        from gevent_zeromq import zmq
    else:
        import zmq  # NOQA
except ImportError:
    zmq = None  # NOQA


REQUEST_TIMEOUT = 2500
REQUEST_RETRIES = 3


class LazyPirateClient(threading.Thread):
    """
    This class is used by the metlog client and runs as a background
    thread.  In the event that the server fails to respond in a timely
    manner, the context is destroyed.
    """
    def __init__(self, ctx, context_shutdown_hook, endpoint):
        threading.Thread.__init__(self)
        #print "I: Connecting to server..."
        self.daemon = True
        self.context = ctx
        self.shutdown_hook = context_shutdown_hook
        self.endpoint = endpoint
        self.poll = zmq.Poller()

    def run(self):
        sequence = 0
        while True:
            retries_left = REQUEST_RETRIES

            self.client = self.context.socket(zmq.REQ)
            self.server_endpoint = self.endpoint
            self.client.connect(self.server_endpoint)
            #print "Connecting to: %s" % self.server_endpoint
            self.poll.register(self.client, zmq.POLLIN)

            while retries_left:
                sequence += 1
                request = str(sequence)
                #print "I: Sending (%s)" % request
                self.client.send(request)

                expect_reply = True
                while expect_reply:
                    socks = dict(self.poll.poll(REQUEST_TIMEOUT))

                    if socks.get(self.client) == zmq.POLLIN:
                        reply = self.client.recv()
                        if not reply:
                            break
                        if int(reply) == sequence:
                            #print "I: Server replied OK (%s)" % reply
                            retries_left = REQUEST_RETRIES
                            expect_reply = False
                            time.sleep(1)
                        else:
                            #print "E: Malformed reply from server: %s" % reply
                            pass

                    else:
                        #print "W: No response from server, retrying..."
                        # Socket is confused. Close and remove it.
                        self.client.setsockopt(zmq.LINGER, 0)
                        self.client.close()
                        self.poll.unregister(self.client)
                        retries_left -= 1
                        if retries_left == 0:
                            #print "E: Server seems to be offline, abandoning"
                            break
                        #print "I: Reconnecting and resending (%s)" % request
                        # Create new connection
                        self.client = self.context.socket(zmq.REQ)
                        self.client.connect(self.server_endpoint)
                        #print "Connecting to: %s" % self.server_endpoint
                        self.poll.register(self.client, zmq.POLLIN)
                        self.client.send(request)
            self.shutdown_hook()
