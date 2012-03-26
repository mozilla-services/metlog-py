import psutil
import socket
import json
import os
import sys
from subprocess import Popen, PIPE
from meliae import loader
from meliae import scanner
import tempfile


class InvalidPIDError(StandardError):
    pass


class OSXPermissionFailure(StandardError):
    pass


def check_osx_perm():
    """
    psutil can't do the right thing on OSX because of weird permissioning rules
    in Darwin.

    http://code.google.com/p/psutil/issues/detail?id=108
    """
    return 'darwin' not in sys.platform or os.getuid() == 0


def supports_iocounters():
    if not hasattr(psutil.Process, 'get_io_counters') or os.name != 'posix':
        return False
    return True


class LazyPSUtil(object):
    """
    This class can only be used *outside* the process that is being inspected
    """
    POLL_INTERVAL = 1.0

    def __init__(self, pid):
        self.pid = pid
        self._process = None

    @property
    def process(self):
        if self._process is None:
            self._process = psutil.Process(self.pid)
            if os.getpid() == self.pid:
                raise InvalidPIDError("Can't run process inspection on itself")
        return self._process

    def get_connections(self):
        connections = []
        for conn in self.process.get_connections():
            if conn.type == socket.SOCK_STREAM:
                type = 'TCP'
            elif conn.type == socket.SOCK_DGRAM:
                type = 'UDP'
            else:
                type = 'UNIX'
            lip, lport = conn.local_address
            if not conn.remote_address:
                rip = rport = '*'
            else:
                rip, rport = conn.remote_address
            connections.append({
                'type': type,
                'status': conn.status,
                'local': '%s:%s' % (lip, lport),
                'remote': '%s:%s' % (rip, rport),
                })
        return connections

    def get_io_counters(self):
        if not supports_iocounters():
            sys.exit('platform not supported')

        io = self.process.get_io_counters()

        return {'read_bytes': io.read_bytes,
                'write_bytes': io.write_bytes,
                'read_count': io.read_count,
                'write_count': io.write_count,
                }

    def get_memory_info(self):
        if not check_osx_perm():
            raise OSXPermissionFailure("OSX requires root for memory info")

        cputimes = self.process.get_cpu_times()
        meminfo = self.process.get_memory_info()
        mem_details = {'mem_pcnt': self.process.get_memory_percent(),
                'rss': meminfo.rss,
                'vms': cputimes.system}
        return mem_details

    def get_cpu_info(self):
        if not check_osx_perm():
            raise OSXPermissionFailure("OSX requires root for memory info")

        cputimes = self.process.get_cpu_times()
        cpu_pcnt = self.process.get_cpu_percent(interval=self.POLL_INTERVAL)
        return {'cpu_pcnt': cpu_pcnt,
                'cpu_user': cputimes.user,
                'cpu_sys': cputimes.system}

    def get_thread_cpuinfo(self):
        if not check_osx_perm():
            raise OSXPermissionFailure("OSX requires root for memory info")

        thread_details = {}
        for thread in self.process.get_threads():
            thread_details[thread.id] = {'sys': thread.system_time,
                    'user': thread.user_time}
        return thread_details

    """
    This seems to crash with a memory pointer error on at least OSX
    def get_open_files(self):
        file_details = []
        for open_file in self.process.get_open_files():
            file_details.append(open_file.path)
        return file_details
    """

    def write_json(self):
        data = {}
        data['network'] = self.get_connections()

        if  supports_iocounters():
            data['io'] = self.get_io_counters()

        if check_osx_perm():
            data['cpu_info'] = self.get_cpu_info()
            data['mem_info'] = self.get_memory_info()
            data['threads'] = self.get_thread_cpuinfo()

        # open files doesn't work in a reliable way
        # data['files'] = self.get_open_files()

        print json.dumps(data)


class Memtool(object):
    """
    This is a wrapper around meliae - a memory profile dumper

    Meliae seems to segfault python in some conditions - it seems primarily in
    ipython, so we have to check and throw errors for those conditions
    """
    def dump_all_objects(self):
        """
        This is very expensive (3 calls per second on a laptop).

        Probably can't fire off a background thread to invoke this either since
        the scanner is going to hit gc.get_objects() which probably pauses the
        world.
        """
        fout = tempfile.NamedTemporaryFile(suffix='.json', delete=True)
        fname = fout.name
        scanner.dump_all_objects(fname)
        fout.seek(0)
        data = fout.readlines()
        fout.close()
        return data

    def parse_memory(self, data, delete=True):
        '''
        Parse the JSON data for memory info.

        This is very expensive.  Do not do this unless you know what you are
        doing.
        '''
        objects = loader.load(data, show_prog=False)
        objects.compute_parents()
        summary = objects.summarize()

        # meliae has a bug where you can't iterate over the summaries
        # until you stringify the object at least once.
        ignored = str(summary)
        return summary


def process_details(pid=None):
    if pid is None:
        pid = os.getpid()
    interp = sys.executable
    cmd = 'from metlog.procinfo import LazyPSUtil;LazyPSUtil(%d).write_json()'
    cmd = cmd % pid
    proc = Popen([interp, '-c', cmd], stdout=PIPE, stderr=PIPE)
    result = proc.communicate()
    stdout, stderr = result[0], result[1]
    return json.loads(stdout)
