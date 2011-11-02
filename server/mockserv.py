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
subscriber.bind("ipc:///tmp/feeds/0")

print  "Now listening"
while True:
    print "[%s]" % subscriber.recv()
