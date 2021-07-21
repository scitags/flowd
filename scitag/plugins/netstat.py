import logging
import time
import psutil
import ipaddress

import scitag
from scitag.config import config

log = logging.getLogger('scitag')


def init():
    log.debug('init')
    if 'EXPERIMENT' not in config.keys():
        log.error('Experiment is required for netstat partial tagging')
        raise scitag.FlowConfigException('Experiment is required for netstat partial tagging')
    if 'NETSTAT_INTERNAL_NETWORKS' in config.keys():
        for net in config['NETSTAT_INTERNAL_NETWORKS']:
            try:
                ipaddress.ip_network(net)
            except ValueError as e:
                log.error('Unable to parse network {}, configuration error'.format(net))
                raise scitag.FlowConfigException('Unable to parse network {}'.format(net))


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


def run(flow_queue, term_event):
    netstat_prev = set()
    int_networks = set()
    if 'NETSTAT_INTERNAL_NETWORKS' in config.keys():
        for net in config['NETSTAT_INTERNAL_NETWORKS']:
            int_networks.add(ipaddress.ip_network(net))

    while not term_event.is_set():
        netstat = set()
        try:
            netc = psutil.net_connections(kind='tcp')
        except Exception as e:
            log.exception('Exception caught while calling psutil')
            time.sleep(60)
            continue

        for entry in netc:
            if entry.status == 'LISTEN':
                continue
            prot = 'tcp'
            saddr = entry.laddr.ip
            sport = entry.laddr.port
            daddr = entry.raddr.ip
            dport = entry.raddr.port
            try:
                ipaddress.ip_address(saddr)
                ipaddress.ip_address(daddr)
            except ValueError:
                log.debug('Failed to parse IPs: {}/{}'.format(saddr, daddr))
                continue
            netstat.add((prot, saddr, sport, daddr, dport))
        log.debug(netstat)

        if netstat_prev:
            new_connections = netstat - netstat_prev
            closed_connections = netstat_prev - netstat

            for c in new_connections:
                daddr = ipaddress.ip_address(c[3])
                if __int_ip(daddr, int_networks):
                    continue
                f_id = scitag.FlowID('start', *c, config['EXPERIMENT'], None)
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)

            for c in closed_connections:
                daddr = ipaddress.ip_address(c[3])
                if __int_ip(daddr, int_networks):
                    continue
                f_id = scitag.FlowID('end', *c, config['EXPERIMENT'], None)
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)
        else:
            for c in netstat:
                daddr = ipaddress.ip_address(c[3])
                if __int_ip(daddr, int_networks):
                    continue
                f_id = scitag.FlowID('start', *c, config['EXPERIMENT'], None)
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)
        netstat_prev = netstat

        term_event.wait(60)
