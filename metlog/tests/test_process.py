"""
Process specific logging tests

We are initially interested in :
    * network connections with each connection status, 
    * CPU utilization, 
    * thread counts, 
    * child process counts, 
    * memory utilization.
"""


from unittest2 import TestCase
from metlog.procinfo import Memtool
from metlog.procinfo import process_details
from metlog.procinfo import check_osx_perm
from metlog.procinfo import supports_iocounters
import time
import socket
import threading
from nose.tools import eq_

class TestProcessLogs(TestCase):

    def test_connections(self):
        HOST = 'localhost'                 # Symbolic name meaning the local host
        PORT = 50007              # Arbitrary non-privileged port
        def echo_serv():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            s.bind((HOST, PORT))
            s.listen(1)

            conn, addr = s.accept()
            data = conn.recv(1024)
            conn.send(data)
            conn.close()
            s.close()

        t = threading.Thread(target=echo_serv)
        t.start()
        time.sleep(1)

        def client_code():
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((HOST, PORT))
            client.send('Hello, world')
            data = client.recv(1024)
            client.close()
            time.sleep(1)

        details = process_details()
        eq_(len(details['network']), 1)

        # Start the client up just so that the server will die gracefully
        tc = threading.Thread(target=client_code)
        tc.start()

    def test_cpu_info(self):
        if not check_osx_perm():
            self.skipTest("OSX needs root")
        detail = process_details()
        assert 'cpu_pcnt' in detail['cpu_info']
        assert 'cpu_sys' in detail['cpu_info']
        assert 'cpu_user' in detail['cpu_info']

    def test_thread_cpu_info(self):
        if not check_osx_perm():
            self.skipTest("OSX needs root")
        detail = process_details()
        for thread_id, thread_data in detail['threads'].items():
            assert 'sys' in thread_data
            assert 'user' in thread_data

    def test_io_counters(self):
        if not supports_iocounters():
            self.skipTest("No IO counter support on this platform")
        # TODO

    def test_meminfo(self):
        if not check_osx_perm():
            self.skipTest("OSX needs root")

        detail = process_details()
        for thread_id, thread_data in detail['threads'].items():
            assert 'sys' in thread_data
            assert 'user' in thread_data

class TestMemInfo(TestCase):
    def test_memdump(self):
        class TestingMemDummy(object):
            pass
        obj = TestingMemDummy()
        mem = Memtool()
        json_data = mem.dump_all_objects()
        eq_(len([l for l in json_data if '"name": "TestingMemDummy"' in l]), 1)

        summary = mem.parse_memory(json_data)

        # Not sure what else I can really assert on here
        ignored = str(summary)
        test_summary = [s for s in summary.summaries if s.type_str == 'TestingMemDummy']
        assert len(test_summary) == 1
        test_summary = test_summary[0]
        assert test_summary.count == 1
        assert test_summary.total_size == 64
