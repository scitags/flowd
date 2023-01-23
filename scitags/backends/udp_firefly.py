import logging
from datetime import datetime

try:
    import queue
except ImportError:
    import Queue as queue
import socket
import json

from scitags.config import config
import scitags.settings
try:
    import scitags.netlink.cache
except ImportError:
    pass

log = logging.getLogger('scitags')
sock6 = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
sock4 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

SYSLOG_FACILITY_LOCAL0 = 16
SYSLOG_SEVERITY_INFORMATIONAL = 6
SYSLOG_PRIORITY = (SYSLOG_FACILITY_LOCAL0 << 3) | SYSLOG_SEVERITY_INFORMATIONAL
SYSLOG_VERSION = 1
SYSLOG_HOSTNAME = socket.gethostname()
SYSLOG_APP_NAME = "flowd"
SYSLOG_PROCID = "-"
SYSLOG_MSGID = "firefly-json"
SYSLOG_STRUCT_DATA = "-"

NETLINK_ENABLED = False


def firefly_json(flow_id, flow_map, ipconfig, netlink_cache):
    if isinstance(flow_id.exp, int):
        exp_id = flow_id.exp
    elif flow_id.exp in flow_map['experiments'].keys():
        exp_id = flow_map['experiments'][flow_id.exp]
    else:
        err = 'Failed to map experiment ({}) to id'.format(flow_id.exp)
        log.error(err)
        raise scitags.FlowIdException(err)

    if not flow_id.act:
        act_id = 0
    elif isinstance(flow_id.act, int):
        act_id = flow_id.act
    elif flow_id.act in flow_map['activities'][exp_id].keys():
        act_id = flow_map['activities'][exp_id][flow_id.act]
    else:
        err = 'Failed to map activity ({}/{}) to id'.format(flow_id.exp, flow_id.act)
        log.error(err)
        raise scitags.FlowIdException(err)

    if ":" in flow_id.dst:
        afi = 'ipv6'
    else:
        afi = 'ipv4'

    firefly = {
        "version": 1,
        "flow-lifecycle": {
            "state": flow_id.state,
            "current-time": datetime.utcnow().isoformat()+'+00:00',
        },
        "flow-id": {
            "afi": afi,
            "src-ip": flow_id.src,
            "dst-ip": flow_id.dst,
            "protocol": flow_id.prot,
            "src-port": flow_id.src_port,
            "dst-port": flow_id.dst_port,
        },
        "context": {
            "experiment-id": exp_id,
            "activity-id": act_id,
            "application": "flowd v{}".format(scitags.VERSION),
        },
    }
    if flow_id.state == 'start':
        firefly['flow-lifecycle']["start-time"] = flow_id.start_time
    if flow_id.state == 'end':
        firefly['flow-lifecycle']["start-time"] = flow_id.start_time
        firefly['flow-lifecycle']["end-time"] = flow_id.end_time

    if flow_id.netlink:
        firefly['netlink'] = flow_id.netlink
    elif NETLINK_ENABLED and 'tcp' in flow_id.prot and 'start' in flow_id.state:
        scitags.netlink.cache.netlink_cache_add(flow_id.state, flow_id.src, flow_id.src_port,
                                                flow_id.dst, flow_id.dst_port, netlink_cache)
        netlink = netlink_cache[('tcp', flow_id.src, flow_id.src_port, flow_id.dst, flow_id.dst_port)]
        firefly['netlink'] = netlink
    elif NETLINK_ENABLED and 'tcp' in flow_id.prot and 'end' in flow_id.state:
        netlink = netlink_cache[('tcp', flow_id.src, flow_id.src_port, flow_id.dst, flow_id.dst_port)]
        # get last known netlink state
        firefly['netlink'] = netlink
        scitags.netlink.cache.netlink_cache_del(flow_id.src, flow_id.src_port,
                                                flow_id.dst, flow_id.dst_port, netlink_cache)

    if ipconfig and afi == 'ipv6' and ipconfig.pub_ip6:
        firefly['flow-id']['src-ip'] = ipconfig.pub_ip6
    if ipconfig and afi == 'ipv4' and ipconfig.pub_ip4:
        firefly['flow-id']['src-ip'] = ipconfig.pub_ip4

    if afi == 'ipv4' and 'UDP_FIREFLY_IP4_SRC' in config.keys():
        firefly['flow-id']['src-ip'] = config['UDP_FIREFLY_IP4_SRC']
    if afi == 'ipv6' and 'UDP_FIREFLY_IP6_SRC' in config.keys():
        firefly['flow-id']['src-ip'] = config['UDP_FIREFLY_IP6_SRC']
    if 'UDP_FIREFLY_WITH_NETLINK' in config.keys() and config['UDP_FIREFLY_WITH_NETLINK']:
        firefly['netlink'] = flow_id.netlink

    return firefly


def run(flow_queue, term_event, flow_map, ip_config):
    global NETLINK_ENABLED
    netlink_cache = dict()
    init_done = False
    if 'UDP_FIREFLY_NETLINK' in config.keys() and config['UDP_FIREFLY_NETLINK']:
        # note: if udp_firefly runs as pool in the future, netlink will need new implementation
        NETLINK_ENABLED = True
    while not term_event.is_set():
        try:
            flow_id = flow_queue.get(block=True, timeout=0.5)
        except queue.Empty:
            if NETLINK_ENABLED and init_done:
                scitags.netlink.cache.netlink_cache_update(netlink_cache)
            continue

        log.debug(flow_id)

        if 'start' in flow_id.state:
            # first queue event arrived
            init_done = True
        try:
            global sock4, sock6
            if not sock4:
                sock4 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if not sock6:
                sock6 = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            dst = flow_id.dst
            syslog_header = '<{}>{} {} {} {} {} {} {} '.format(SYSLOG_PRIORITY, SYSLOG_VERSION,
                                                               datetime.utcnow().isoformat() + '+00:00',
                                                               SYSLOG_HOSTNAME,
                                                               SYSLOG_APP_NAME, SYSLOG_PROCID, SYSLOG_MSGID,
                                                               SYSLOG_STRUCT_DATA)
            udp_payload = syslog_header + json.dumps(firefly_json(flow_id, flow_map, ip_config, netlink_cache))
            log.debug(udp_payload)
            if ':' in flow_id.dst:
                sock6.sendto(udp_payload.encode('utf-8'), (dst, scitags.settings.UDP_FIREFLY_PORT))
            else:
                sock4.sendto(udp_payload.encode('utf-8'), (dst, scitags.settings.UDP_FIREFLY_PORT))
            if 'UDP_FIREFLY_DST' in config.keys():
                dst = config['UDP_FIREFLY_DST']
                sock4.sendto(udp_payload.encode('utf-8'), (dst, scitags.settings.UDP_FIREFLY_PORT))
        except Exception as e:
            log.exception(e)
