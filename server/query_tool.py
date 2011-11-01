import sys
import zmq
import time
import json

bind_str = "ipc:///tmp/feeds/1"
zmq_context = zmq.Context()
pub = zmq_context.socket(zmq.PUB)
pub.bind(bind_str)
jdata = {'logger': '',
        'cmd': 'LOGGER_INFO',
        }
jstr = json.dumps(jdata)
while True:
    pub.send(jstr)

