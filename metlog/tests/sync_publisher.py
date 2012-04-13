#
# Synchronized publisher. This is like a metlog cliennt
#
import zmq
import sys

def main():
    context = zmq.Context()

    # Socket to talk to clients
    publisher = context.socket(zmq.PUB)
    publisher.connect('tcp://localhost:5561')
    publisher.setsockopt(zmq.LINGER, 0)

    # Socket to receive signals
    syncservice = context.socket(zmq.REQ)
    syncservice.connect('tcp://localhost:5562')
    syncservice.setsockopt(zmq.LINGER, 0)

    poll = zmq.Poller()
    poll.register(syncservice, zmq.POLLIN)

    # send synchronization request
    print "Sending Sync Request"

    syncservice.send("")
    socks = dict(poll.poll(200))
    if socks.get(syncservice) == zmq.POLLIN:
        # The server is there
        print "Y: PollIN is ok"
        syncservice.recv()

        # Now broadcast exactly 1M updates followed by END
        for i in range(1000000):
            publisher.send('Rhubarb');

        publisher.send('END')
    else:
        # The server is not there
        # Socket is confused. Close and remove it.
        syncservice.setsockopt(zmq.LINGER, 0)
        publisher.setsockopt(zmq.LINGER, 0)
        syncservice.close()
        publisher.close()

if __name__ == '__main__':
    main()

