
#
# Synchronized subscriber. This is like logstash
#
import zmq
import threading

context = zmq.Context()

def sync_thread():
    # Second, synchronize with publisher
    syncclient = context.socket(zmq.REP)
    syncclient.bind('tcp://*:5562')

    while True:
        # wait for a synchronization request
        syncclient.recv()

        # send synchronization reply
        syncclient.send('')

def main():

    # First, connect our subscriber socket
    subscriber = context.socket(zmq.SUB)
    subscriber.bind('tcp://*:5561')
    subscriber.setsockopt(zmq.SUBSCRIBE, "")

    t = threading.Thread(target=sync_thread)
    t.daemon = True
    t.start()


    # Third, get our updates and report how many we got
    nbr = 0
    while True:
        msg = subscriber.recv()
        if msg == 'END':
            break
        nbr += 1

    print 'Received %d updates' % nbr

if __name__ == '__main__':
    main()

