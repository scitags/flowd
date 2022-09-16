import logging
import time
import ipaddress
import pprint
from datetime import datetime
from pyroute2.netlink.diag import DiagSocket
from pyroute2.netlink.diag import SS_CONN

import scitags
import scitags.settings
from scitags.netlink import TCP
from scitags.config import config

log = logging.getLogger('scitags')


def init():
    log.debug('init')
    if 'NETSTAT_EXPERIMENT' not in config.keys():
        log.error('Experiment is required for netlink partial tagging')
        raise scitags.FlowConfigException('Experiment is required for netlink partial tagging')

    if 'NETSTAT_ACTIVITY' not in config.keys():
        log.error('Activity is required for netlink partial tagging')
        raise scitags.FlowConfigException('Activity is required for netlink partial tagging')

    if 'NETSTAT_INTERNAL_NETWORKS' in config.keys():
        for net in config['NETSTAT_INTERNAL_NETWORKS']:
            try:
                ipaddress.ip_network(u'{}'.format(net))
            except ValueError as e:
                log.error('Unable to parse network {}, configuration error'.format(net))
                raise scitags.FlowConfigException('Unable to parse network {}'.format(net))
    log.info('   netlink init: done')


def __int_ip(ip, int_networks):
    if ip.is_private:
        return True
    for net in int_networks:
        if type(ip) is ipaddress.IPv4Address and type(net) is ipaddress.IPv4Network \
                and ip in net:
            return True
        if type(ip) is ipaddress.IPv6Address and type(net) is ipaddress.IPv6Network \
                and ip in net:
            return True
    return False


def run(flow_queue, term_event, ip_config):
    netlink_index = dict()
    int_networks = set()
    init_pass = True
    if 'NETSTAT_INTERNAL_NETWORKS' in config.keys():
        for net in config['NETSTAT_INTERNAL_NETWORKS']:
            int_networks.add(ipaddress.ip_network(u'{}'.format(net)))

    while not term_event.is_set():
        netlink = dict()
        try:
            with DiagSocket() as ds:
                ds.bind()
                p = TCP(sk_states=SS_CONN)
                netc = p(ds)
        except Exception as e:
            log.exception('Exception caught while querying netlink')
            time.sleep(scitags.settings.NETLINK_TIMEOUT)
            continue

        for entry in netc:
            if 'tcp_info' not in entry:
                continue
            prot = 'tcp'
            saddr = u'{}'.format(entry['src'])
            sport = entry['src_port']
            daddr = u'{}'.format(entry['dst'])
            dport = entry['dst_port']
            status = entry['tcp_info']['state']
            try:
                ipaddress.ip_address(saddr)
                ipaddress.ip_address(daddr)
            except ValueError as e:
                log.debug('Failed to parse IPs: {}/{}'.format(saddr, daddr))
                log.exception(e)
                continue
            netlink[(prot, saddr, sport, daddr, dport)] = (status, entry)
        log.debug('    netlink query: {}'.format(len(netlink)))
        #log.debug(pprint.pformat(netlink))

        if init_pass:
            # register existing connections - don't trigger any fireflies as
            # we don't have start_time for them
            init_pass = False
            for k, v in netlink.items():
                daddr = ipaddress.ip_address(k[3])
                if __int_ip(daddr, int_networks):
                    continue
                netlink_index[k] = dict()
                netlink_index[k]['status'] = v[0]
                netlink_index[k]['start_time'] = None
                netlink_index[k]['end_time'] = None
                netlink_index[k]['netlink'] = v[1]
                continue
            log.debug('  netlink cache: {}'.format(len(netlink_index)))
            time.sleep(scitags.settings.NETLINK_TIMEOUT)

        for k, v in netlink.items():
            daddr = ipaddress.ip_address(k[3])
            if __int_ip(daddr, int_networks):
                continue
            if k not in netlink_index.keys() and v[0] == 'established':
                netlink_index[k] = dict()
                netlink_index[k]['status'] = v[0]
                netlink_index[k]['start_time'] = datetime.utcnow().isoformat()+'+00:00'
                netlink_index[k]['end_time'] = None
                netlink_index[k]['netlink'] = v[1]
                f_id = scitags.FlowID('start', *k + (config['NETSTAT_EXPERIMENT'], config['NETSTAT_ACTIVITY'],
                                                     netlink_index[k]['start_time'], None, netlink_index[k]['netlink']))
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)
            elif k in netlink_index.keys() and v == 'established':
                # update netlink info for known connections
                netlink_index[k]['netlink'] = v[1]

        # cleanup
        closed_connections = set(netlink_index.keys()) - set(netlink.keys())
        for c in closed_connections:
            log.debug(closed_connections)
            # connections where we didn't catch end state ?
            if netlink_index[c]['start_time'] and not netlink_index[c]['end_time']:
                netlink_index[c]['end_time'] = datetime.utcnow().isoformat() + '+00:00'
                f_id = scitags.FlowID('end', *c + (config['NETSTAT_EXPERIMENT'], config['NETSTAT_ACTIVITY'],
                                                   netlink_index[c]['start_time'], netlink_index[c]['end_time'],
                                                   netlink_index[c]['netlink']))
                log.debug('   <-- {}'.format(f_id))
                flow_queue.put(f_id)
            netlink_index.pop(c, None)

        term_event.wait(scitags.settings.NETLINK_TIMEOUT)
