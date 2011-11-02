
from metlog.client import MetlogClient
from metlog.senders import ZmqPubSender
from metlog.backchannel import ZmqBackchannel
import time
import os

SUB_BIND, PUB_BIND = "ipc:///tmp/feeds/1", "ipc:///tmp/feeds/2"
bc = ZmqBackchannel(SUB_BIND, PUB_BIND)

sender = ZmqPubSender("ipc:///tmp/feeds/0")
client = MetlogClient(sender, back_channel=bc)
while True:
    time.sleep(1)
    client.metlog("msg_type", payload="pid [%d]" % os.getpid())
    print "send messages"

