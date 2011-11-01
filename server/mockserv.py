"""
This is a dummy 0mq server that just read messages from the PUB/SUB
interface
"""
import sys
import zmq
import time

zmq_context = zmq.Context()
subscriber = zmq_context.socket(zmq.SUB)
subscriber.setsockopt(zmq.SUBSCRIBE, "")
subscriber.setsockopt(zmq.HWM, 10)
subscriber.connect("ipc:///tmp/feeds/0")

print  "Now listening"
while True:
    try:
        print "[%s]" % subscriber.recv(zmq.NOBLOCK)
    except zmq.ZMQError, zmq_err:
        sys.stdout.write(".")
        time.sleep(0.1)
