"""
This is a dummy 0mq server that just read messages from the PUB/SUB
interface
"""
import sys
import zmq
import time
import os

zmq_context = zmq.Context()
pusher = zmq_context.socket(zmq.PUSH)
pusher.bind("ipc:///tmp/feeds/0")

print  "Now pushing messages"
i = 0
while True:
    i += 1
    pusher.send("[%05d] %d" % (i, os.getpid()))
    time.sleep(1)
