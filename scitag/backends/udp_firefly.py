import logging
import queue
import socket
import json

from scitag.config import config
import scitag.settings

log = logging.getLogger('scitag')


def run(flow_queue, term_event):
    while not term_event.is_set():
        try:
            flow_id = flow_queue.get(block=True, timeout=0.5)
        except queue.Empty:
            continue

        log.debug(flow_id)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dst = flow_id.dst
        if 'UDP_FIREFLY_DST' in config.keys():
            dst = config['UDP_FIREFLY_DST']
        udp_flow_id = json.dumps(flow_id._asdict())
        sock.sendto(udp_flow_id.encode('utf-8'), (dst, scitag.settings.UDP_FIREFLY_PORT))
