import unittest
import logging
import sys

import scitags
import multiprocessing

log = logging.getLogger("wnfm")
log.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(message)s')
fh = logging.StreamHandler(stream=sys.stdout)
fh.setFormatter(formatter)
log.addHandler(fh)


class TestScitags(unittest.TestCase):

    @staticmethod
    def worker(q):
        flow_id = scitags.FlowID('start', 'tcp', '127.0.0.1', 1, '127.0.0.1', 1, 1, 1)
        for item in iter(q.get, None):
            assert item == flow_id

    def test_queue(self):
        queue = scitags.PubSubQueue()
        flow_id = scitags.FlowID('start', 'tcp', '127.0.0.1', 1, '127.0.0.1', 1, 1, 1)
        processes = []
        for _ in range(3):
            p = multiprocessing.Process(target=TestScitags.worker, args=(queue.register(),))
            p.start()
            processes.append(p)
        queue.put(flow_id)
        queue.put(flow_id)
        queue.put(None)  # Shut down workers

        for p in processes:
            p.join()


if __name__ == '__main__':
    unittest.main()
