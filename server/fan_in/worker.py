"""
This is a dummy 0mq server that just read messages from the PUB/SUB
interface
"""
import sys
import zmq
import time
import os

zmq_context = zmq.Context()
sender = zmq_context.socket(zmq.PUB)
sender.connect("ipc:///tmp/feeds/0")

print  "Now sending"
while True:
    sender.send("[%d]" % os.getpid())
    time.sleep(1)
