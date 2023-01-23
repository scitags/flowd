import socketserver
import threading
import logging
import scitags.settings
import json
import time

from scitags.config import config

log = logging.getLogger('scitags')


class ThreadedUDPRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        data = self.request[0].strip()
        current_thread = threading.current_thread()
        print("{}: client: {}, wrote: {}".format(current_thread.name, self.client_address, data))
        if b'firefly-json' not in data:
            log.debug("Ignoring incoming firefly {}".format(data))
            return
        syslog_header = data.decode().split(" ")
        if len(syslog_header) <= 7:
            log.debug("Failed to parse incoming firefly {}".format(data))
            return
        firefly_json = json.loads(" ".join(syslog_header[7:]))
        state = firefly_json['flow-lifecycle']['state']
        protocol = firefly_json['flow-id']['protocol']
        src = firefly_json['flow-id']['src-ip']
        src_port = firefly_json['flow-id']['src-port']
        dst = firefly_json['flow-id']['dst-ip']
        dst_port = firefly_json['flow-id']['dst-port']
        exp = firefly_json['context']['experiment-id']
        activity = firefly_json['context']['activity-id']
        start_time = None
        end_time = None
        if state == 'start':
            start_time = firefly_json['flow-lifecycle']["start-time"]
        if state == 'end':
            start_time = firefly_json['flow-lifecycle']["start-time"]
            end_time = firefly_json['flow-lifecycle']["end-time"]

        flow_id = scitags.FlowID(state, protocol, src, src_port, dst, dst_port, exp, activity, start_time, end_time)
        log.debug('   --> {}'.format(flow_id))
        self.server.queue.put(flow_id)


class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    def __init__(self, host_port_tuple, handler, queue):
        super().__init__(host_port_tuple, handler)
        self.queue = queue


def init():
    log.debug('firefly listener init')


def run(flow_queue, term_event, ip_config):
    if 'FIREFLY_LISTENER_HOST' in config.keys():
        host = config['FIREFLY_LISTENER_HOST']
    else:
        host = scitags.settings.FIREFLY_LISTENER_HOST
    if 'FIREFLY_LISTENER_PORT' in config.keys():
        port = config['FIREFLY_LISTENER_PORT']
    else:
        port = scitags.settings.FIREFLY_LISTENER_PORT

    server = ThreadedUDPServer((host, port), ThreadedUDPRequestHandler, flow_queue)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True

    server_thread.start()
    log.debug("firefly listener started @{}/{}".format(host, port))
    while not term_event.is_set():
        time.sleep(2)

    server.shutdown()
    server.server_close()
