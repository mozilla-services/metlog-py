import timeit
from metlog.decorators.process import Memtool

mem = Memtool()
json_lines = mem.dump_memory()
result = mem.parse_memory(json_lines)
print result
