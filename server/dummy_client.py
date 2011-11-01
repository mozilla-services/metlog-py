
from metlog.client import MetlogClient
from metlog.senders import ZmqPubSender
from metlog.backchannel import ZmqBackchannel
import time

bc = ZmqBackchannel("ipc:///tmp/feeds/1")
sender = ZmqPubSender("ipc:///tmp/feeds/0")
client = MetlogClient(sender, back_channel=bc)
for i in range(2000):
    time.sleep(1)
    client.metlog("msg_type", payload="foo load [%d]" % i)

