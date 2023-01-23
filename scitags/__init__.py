import collections
import os
import multiprocessing as mp
try:
    import queue
except ImportError:
    import Queue as queue

AUTHOR = "Marian Babik <Marian.Babik@cern.ch>, "
AUTHOR_EMAIL = "<net-wg-dev@cern.ch>"
COPYRIGHT = "Copyright (C) 2021"
VERSION = "0.1.3"
DATE = "13 Jul 2021"
__author__ = AUTHOR
__version__ = VERSION
__date__ = DATE


class FlowConfigException(Exception):
    pass


class FlowIdException(Exception):
    pass


# Flow Identifier
# flow-start
#   inputs: (protocol, src, src_port, dst, dst_port, experiment, activity)
# flow-end
#   inputs: (protocol, src, src_port, dst, dst_port, experiment, activity)
# flow-update (optional)
#   inputs: (protocol, src, src_port, dst, dst_port, experiment, activity)
FlowID = collections.namedtuple('FlowID', ['state', 'prot', 'src', 'src_port', 'dst', 'dst_port', 'exp', 'act',
                                           'start_time', 'end_time', 'netlink'])
FlowID.__new__.__defaults__ = (None,) * 3   # start_time/end_time/netlink default to None


# IP config container
IPConfig = collections.namedtuple('ip_config', ['pub_ip4', 'int_ip4', 'pub_ip6', 'int_ip6'])

# Publish/Subscribe Multiprocessing Queue
class PubSubQueue(object):
    def __init__(self):
        self._queues = []
        self._creator_pid = os.getpid()

    def __getstate__(self):
        self_dict = self.__dict__
        self_dict['_queues'] = []
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)

    def register(self):
        q = mp.Queue()
        self._queues.append(q)
        return q

    def put(self, val):
        for q in self._queues:
            q.put(val)

    def close(self):
        while True:
            try:
                for q in self._queues:
                    q.get(block=False)
            except queue.Empty:
                break
            except ValueError:
                break
        for q in self._queues:
            q.close()
            q.join_thread()

