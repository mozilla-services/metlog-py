#
# Synchronized publisher. This is like a metlog cliennt
#
import zmq
import sys

def main():
    context = zmq.Context()

    # Socket to talk to clients
    publisher = context.socket(zmq.PUB)
    publisher.bind('tcp://*:5561')

    # Socket to receive signals
    syncservice = context.socket(zmq.REQ)
    syncservice.bind('tcp://*:5562')

    # send synchronization request
    print "Sending Sync Request"

    poll = zmq.Poller()
    poll.register(syncservice, zmq.POLLOUT)
    print "Polling before sending sync request"
    events = poll.poll(100)
    if len(events) == 0:
        print "No server is visible"
        sys.exit(0)

    poll.unregister(syncservice)

    print "Poll results: %s" % str(events)

    syncservice.send("")
    syncservice.recv()


    # Now broadcast exactly 1M updates followed by END
    for i in range(1000000):
        publisher.send('Rhubarb');

    publisher.send('END')

if __name__ == '__main__':
    main()

