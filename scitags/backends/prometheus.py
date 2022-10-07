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
    def __init__(self, netlink_cache, flow_cache, exp_index, act_index):
        self.netlink_cache = netlink_cache
        self.flow_cache = flow_cache
        self.exp_index = exp_index
        self.act_index = act_index

    def collect(self):
        labels = ['src', 'dst', 'exp', 'act']
        log.debug('prometheus collect')
        log.debug(self.netlink_cache)
        for c, ci in self.netlink_cache.items():
            src = c[1]
            src_port = c[2]
            dst = c[3]
            dst_port = c[4]
            log.debug(c)
            if (src, src_port, dst, dst_port) in self.flow_cache.keys():
                e_id, a_id = self.flow_cache[(src, src_port, dst, dst_port)]
                exp = self.exp_index[e_id]
                act = self.act_index[e_id][a_id]
            else:
                exp = 'default'
                act = 'default'
            for k, v in ci[1]['tcp_info'].items():
                if isinstance(v, int) and k:
                    if any(x in k for x in ['bytes', 'segs', 'retrans']):
                        counter = prometheus_client.core.CounterMetricFamily('flow_tcp_'+k, '', labels=labels)
                        counter.add_metric((src, dst, exp, act), v)
                        yield counter
                    else:
                        gauge = prometheus_client.core.GaugeMetricFamily('flow_tcp_'+k, '', labels=labels)
                        gauge.add_metric((src, dst, exp, act), v)
                        yield gauge
            info = prometheus_client.core.InfoMetricFamily('flow_tcp_ca', '', labels=labels)
            info.add_metric((src, dst, exp, act), {'cong_algo': ci[1]['cong_algo']})
            info.add_metric((src, dst, exp, act), {'opts': ' '.join(ci[1]['tcp_info']['opts'])})
            yield info
                #else:
                #    info = prometheus_client.core.InfoMetricFamily('flow_tcp_', '', labels=labels)
                #    log.debug(k, v)
                #    info.add_metric((src, dst, e_id, a_id), {k: v})
                #    yield info
                # flow_id = prometheus_client.core.InfoMetricFamily('flow_tcp_', '', labels=labels)
                # info.add_metric((src, dst, e_id, a_id), {'experiment' : flow_map[e_id]})
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
    flow_cache = dict()
    # flow_map indexes
    exp_index = {y: x for x, y in flow_map['experiments'].items()}
    act_index = dict()
    for k, v in flow_map['activities'].items():
        act_index[k] = {y: x for x, y in v.items()}
    log.debug(exp_index)
    log.debug(act_index)
    # create another dict that holds flow to exp+act mapping 
    netlink_plugin = 'netlink' in config['PLUGIN']
    init_done = False
    prometheus_client.core.REGISTRY.register(FlowCollector(netlink_cache, flow_cache, exp_index, act_index))
    log.debug('prometheus client started on 0.0.0.0:{}'.format(port))
    log.debug('entering event loop')
    while not term_event.is_set():
        try:
            flow_id = flow_queue.get(block=True, timeout=0.5)
        except queue.Empty:
            if not netlink_plugin and init_done:
                scitags.netlink.cache.netlink_cache_update(netlink_cache)
            continue
        log.debug(flow_id)

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
            flow_cache[(flow_id.src, flow_id.src_port, flow_id.dst, flow_id.dst_port)] = (flow_id.exp, flow_id.act)
        elif 'end' in flow_id.state and not flow_id.netlink:
            scitags.netlink.cache.netlink_cache_del(flow_id.src, flow_id.src_port, flow_id.dst,
                                                    flow_id.dst_port, netlink_cache)
            if (flow_id.src, flow_id.src_port, flow_id.dst, flow_id.dst_port) in flow_cache.keys():
                del flow_cache[(flow_id.src, flow_id.src_port, flow_id.dst, flow_id.dst_port)]




