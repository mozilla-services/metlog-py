import sys
import zmq
import time
import json
import threading

BIND_STR = "ipc:///tmp/feeds/1"
CALLBACKBIND_STR = "ipc:///tmp/feeds/2"

zmq_context = zmq.Context()

class QueryTool(object):
    def __init__(self):
        self.pub = zmq_context.socket(zmq.PUB)
        self.pub.bind(BIND_STR)

        self.sub = zmq_context.socket(zmq.PULL)
        self.sub.bind(CALLBACKBIND_STR)

    def query_loggers(self):
        jdata = {'logger': '',
                'cmd': 'LOGGER_INFO',
                }
        jstr = json.dumps(jdata)
        self.pub.send(jstr)

    def responses(self):
        try:
            return self.sub.recv(zmq.NOBLOCK)
        except zmq.ZMQError, zmq_err:
            pass


qt = QueryTool()

qt.query_loggers()
while True:
    time.sleep(1)
    qt.query_loggers()
    print "Requeried.."

    try_again = 5
    while True:
        msg = qt.responses()
        if msg:
            print "Got back: [%s]" % msg
        else:
            try_again -= 1
            time.sleep(0.1)
        if try_again == 0:
            break
    print '=' * 20
