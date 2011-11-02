"""
This is a dummy 0mq server that just read messages from the PUB/SUB
interface
"""
import sys
import zmq
import time

zmq_context = zmq.Context()
subscriber = zmq_context.socket(zmq.PULL)
subscriber.bind("ipc:///tmp/feeds/0")

print  "Now listening"
for i in range(50):
    print "[%s]" % subscriber.recv()
