import logging
try:
    import queue
except ImportError:
    import Queue as queue
import prometheus_client
import prometheus_client.core

import scitags.netlink.cache
import scitags.settings
from scitags.config import config

log = logging.getLogger('scitags')

# todo: override prometheus.start_http_server so we have a way how to shut it down
# def start_wsgi_server(port: int, addr: str = '0.0.0.0', registry: CollectorRegistry = REGISTRY) -> None:
#     """Starts a WSGI server for prometheus metrics as a daemon thread."""
#
#     class TmpServer(ThreadingWSGIServer):
#         """Copy of ThreadingWSGIServer to update address_family locally"""
#
#     TmpServer.address_family, addr = _get_best_family(addr, port)
#     app = make_wsgi_app(registry)
#     httpd = make_server(addr, port, app, TmpServer, handler_class=_SilentHandler)
#     t = threading.Thread(target=httpd.serve_forever)
#     t.daemon = True
#     t.start()


class FlowCollector(object):
    def __init__(self, netlink_cache):
        self.netlink_cache = netlink_cache

    def collect(self):
        labels = ['src', 'dst', 'exp_id', 'activity_id']
        log.debug('prometheus collect')
        log.debug(self.netlink_cache)
        for c, ci in self.netlink_cache.items():
            src = c[1]
            dst = c[3]
            e_id = '1'
            a_id = '1'
            for k, v in ci[1]['tcp_info'].items():
                if isinstance(v, int) and k:
                    gauge = prometheus_client.core.GaugeMetricFamily('flow_tcp_'+k, '', labels=labels)
                    gauge.add_metric((src, dst, e_id, a_id), v)
                    yield gauge
                #else:
                #    info = prometheus_client.core.InfoMetricFamily('flow_tcp_'+k, '', labels=labels)
                #    log.debug(k, v)
                #    info.add_metric((src, dst, e_id, a_id), v)
                #    yield info
            #info = prometheus_client.core.InfoMetricFamily('flow_tcp_cong_algo', '', labels=labels)
            #info.add_metric((src, dst, e_id, a_id), ci[1]['cong_algo'])
            #yield info


def run(flow_queue, term_event, flow_map, ip_config):
    if 'PROMETHEUS_SRV_PORT' in config.keys():
        port = config['PROMETHEUS_SRV_PORT']
    else:
        port = scitags.settings.PROMETHEUS_SRV_PORT
    prometheus_client.start_http_server(port)
    netlink_cache = dict()
    netlink_plugin = 'netlink' in config['PLUGIN']
    init_done = False
    prometheus_client.core.REGISTRY.register(FlowCollector(netlink_cache))
    log.debug('prometheus client started on 0.0.0.0:{}'.format(port))
    log.debug('entering event loop')
    while not term_event.is_set():
        try:
            flow_id = flow_queue.get(block=True, timeout=0.5)
        except queue.Empty:
            if not netlink_plugin and init_done:
                scitags.netlink.cache.netlink_cache_update(netlink_cache)
            continue

        if 'start' in flow_id.state and flow_id.netlink:
            init_done = True
            netlink_cache[(flow_id.src, flow_id.src_port,
                           flow_id.dst, flow_id.dst_port)] = (flow_id.state, flow_id.netlink)
        elif 'end' in flow_id.state and flow_id.netlink:
            del netlink_cache[(flow_id.src, flow_id.src_port, flow_id.dst, flow_id.dst_port)]
        elif 'start' in flow_id.state and not flow_id.netlink:
            init_done = True
            scitags.netlink.cache.netlink_cache_add(flow_id.state, flow_id.src, flow_id.src_port, flow_id.dst,
                                                    flow_id.dst_port, netlink_cache)
        elif 'end' in flow_id.state and not flow_id.netlink:
            scitags.netlink.cache.netlink_cache_del(flow_id.src, flow_id.src_port, flow_id.dst,
                                                    flow_id.dst_port, netlink_cache)




