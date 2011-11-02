"""
This is a dummy 0mq server that just read messages from the PUB/SUB
interface
"""
import sys
import zmq
import time
import os
import random

zmq_context = zmq.Context()
puller = zmq_context.socket(zmq.SUB)
puller.setsockopt(zmq.SUBSCRIBE, "")
puller.connect("ipc:///tmp/feeds/1")

print  "Now receiving"
while True:
    print "Got: [%s] [%s]" % (puller.recv(), random.random())
