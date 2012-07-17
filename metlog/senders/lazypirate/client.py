# Lazy Pirate client
# Use zmq_poll to do a safe request-reply
# To run, start lpserver and then randomly kill/restart it
#
# Author: Daniel Lundin <dln(at)eintr(dot)org>
#

import zmq
import threading

REQUEST_TIMEOUT = 2500
REQUEST_RETRIES = 3


class LazyPirateClient(threading.Thread):
    """
    This class is used by the metlog client and runs as a background
    thread.  In the event that the server fails to respond in a timely
    manner, the context is destroyed.
    """
    def __init__(self, ctx, context_shutdown_hook, endpoint,
            daemon=False):
        threading.Thread.__init__(self)
        print "I: Connecting to server..."
        self.daemon = daemon
        self.context = ctx
        self.shutdown_hook = context_shutdown_hook
        self.poll = zmq.Poller()

    def run(self):
        sequence = 0
        while True:
            retries_left = REQUEST_RETRIES

            self.client = self.context.socket(zmq.REQ)
            self.server_endpoint = endpoint
            self.client.connect(self.server_endpoint)
            self.poll.register(self.client, zmq.POLLIN)

            while retries_left:
                sequence += 1
                request = str(sequence)
                print "I: Sending (%s)" % request
                self.client.send(request)

                expect_reply = True
                while expect_reply:
                    socks = dict(self.poll.poll(REQUEST_TIMEOUT))

                    if socks.get(self.client) == zmq.POLLIN:
                        reply = self.client.recv()
                        if not reply:
                            break
                        if int(reply) == sequence:
                            print "I: Server replied OK (%s)" % reply
                            retries_left = REQUEST_RETRIES
                            expect_reply = False
                        else:
                            print "E: Malformed reply from server: %s" % reply

                    else:
                        print "W: No response from server, retrying..."
                        # Socket is confused. Close and remove it.
                        self.client.setsockopt(zmq.LINGER, 0)
                        self.client.close()
                        self.poll.unregister(self.client)
                        retries_left -= 1
                        if retries_left == 0:
                            print "E: Server seems to be offline, abandoning"
                            break
                        print "I: Reconnecting and resending (%s)" % request
                        # Create new connection
                        self.client = self.context.socket(zmq.REQ)
                        self.client.connect(self.server_endpoint)
                        self.poll.register(self.client, zmq.POLLIN)
                        self.client.send(request)
            self.shutdown_hook()

if __name__ == '__main__':

    # Set 20 background threads
    context = zmq.Context(20)

    def shutdown_hook():
        # TODO: shutdown any other sockets here
        print "I: This should tell all clients to close their sockets"
        pass

    endpoint = "tcp://localhost:5555"

    pirate = LazyPirateClient(context, shutdown_hook, endpoint)
    pirate.start()
