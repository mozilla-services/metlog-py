#
# Synchronized publisher. This is like a metlog cliennt
#
import zmq

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
    syncservice.send('')
    print "Sync Request sent!"

    # wait for synchronization reply
    syncservice.recv()
    print "+1 subscriber"

    # Now broadcast exactly 1M updates followed by END
    for i in range(1000000):
        publisher.send('Rhubarb');

    publisher.send('END')

if __name__ == '__main__':
    main()

