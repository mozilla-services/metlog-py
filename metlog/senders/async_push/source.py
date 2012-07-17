"""
This is a dummy 0mq server that just read messages from the PUB/SUB
interface
"""
import zmq
import time
import os
import threading
import Queue

URL = 'tcp://127.0.0.1:5565'


class NullObject(object):
    pass


class AsyncSender(threading.Thread):
    """
    Public API:

    Only do these things:
        1) Put objects into the queue.
        2) Set the shutdown flag
        3) Set the reconnect flag to close the socket and open a new one
    """
    def __init__(self, ctx, queue, zeromq_url):
        threading.Thread.__init__(self)

        self.daemon = True
        self.context = ctx
        self.queue = queue
        self.zeromq_url = zeromq_url

        self._shutdown_connect_mutex = threading.RLock()
        self._reconnect_mutex = threading.RLock()

        self.shutdown_connection = False
        self.reconnect = False

    def connect(self):
        # This should *only* be called from the run loop of
        # AsyncSender

        self.sender = self.context.socket(zmq.PUSH)
        self.sender.setsockopt(zmq.LINGER, 0)
        self.sender.setsockopt(zmq.HWM, 3)
        self.sender.connect(self.zeromq_url)

        self.reconnect = False
        print "Connected sender"

    def disconnect(self):
        # This should *only* be called from the run loop of
        # AsyncSender
        try:
            self.sender.close()
            print "Disconnected sender: %s" % time.time()
        except zmq.ZMQError, zmq_e:
            print "Error disconnecting socket: %s" % zmq_e
            pass

    def set_reconnect(self, value):
        with self._reconnect_mutex:
            self._reconnect = value

    def get_reconnect(self):
        with self._reconnect_mutex:
            result = self._reconnect
        return result

    # setup a synchronized property so that other threads can tell the
    # async sender to disconnect
    # This is only set to True when the heartbeat process
    # detects that the server has gone away
    reconnect = property(get_reconnect, set_reconnect)

    def set_shutdown_connection(self, value):
        with self._shutdown_connect_mutex:
            self._shutdown_connection = value

    def get_shutdown_connection(self):
        with self._shutdown_connect_mutex:
            result = self._shutdown_connection
        return result

    # setup a synchronized property so that other threads can tell the
    # async sender to disconnect
    shutdown_connection = property(get_shutdown_connection,
            set_shutdown_connection)

    def run(self):
        self.connect()
        while True:
            msg = NullObject
            try:
                # This timeout is in seconds
                msg = self.queue.get(timeout=0.001)

                # we mark the task as done right away since we'll
                # just route the msg to the logger if things go wrong
                # anyway
                self.queue.task_done()
            except Queue.Empty, ignored:   # NOQA
                # The queue is empty - that's ok - we need to be able
                # to terminate sockets if we are blocked on the queue
                pass

            if msg != NullObject:
                try:
                    print "sending msg"
                    self.sender.send(msg, flags=zmq.NOBLOCK, track=True)
                except zmq.core.error.ZMQError, zmq_e:
                    # This error gets thrown for *any* 0mq error. Just
                    # log it.  We can't reconnect here because the
                    # errors will just keep coming for a bit because
                    # of lazy joiner problems
                    print "Exception: [%s]" % zmq_e

            if self.shutdown_connection:
                self.disconnect()
                break

            if self.reconnect:
                self.disconnect()
                self.connect()

        print "Ending runloop"


def main():
    queue = Queue.Queue(500)

    zmq_context = zmq.Context()
    url = 'tcp://127.0.0.1:5565'

    sender = AsyncSender(zmq_context, queue, url)
    sender.start()

    for i in range(20):
        queue.put("[%d]" % os.getpid())
        time.sleep(1)

    sender.shutdown_connection = True


if __name__ == '__main__':
    main()
