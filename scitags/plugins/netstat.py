import logging
import time
import psutil
import ipaddress

import scitags
import scitags.settings
from scitags.config import config

log = logging.getLogger('scitags')


def init():
    log.debug('init')
    if 'NETSTAT_EXPERIMENT' not in config.keys():
        log.error('Experiment is required for netstat partial tagging')
        raise scitags.FlowConfigException('Experiment is required for netstat partial tagging')

    if 'NETSTAT_ACTIVITY' not in config.keys():
        log.error('Activity is required for netstat partial tagging')
        raise scitags.FlowConfigException('Activity is required for netstat partial tagging')

    if 'NETSTAT_INTERNAL_NETWORKS' in config.keys():
        for net in config['NETSTAT_INTERNAL_NETWORKS']:
            try:
                ipaddress.ip_network(net)
            except ValueError as e:
                log.error('Unable to parse network {}, configuration error'.format(net))
                raise scitags.FlowConfigException('Unable to parse network {}'.format(net))
    log.info('   netstat init: done')


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
    netstat_prev = set()
    int_networks = set()
    init_pass = True
    if 'NETSTAT_INTERNAL_NETWORKS' in config.keys():
        for net in config['NETSTAT_INTERNAL_NETWORKS']:
            int_networks.add(ipaddress.ip_network(net))

    while not term_event.is_set():
        netstat = set()
        netstat_status = dict()
        try:
            netc = psutil.net_connections(kind='tcp')
        except Exception as e:
            log.exception('Exception caught while calling psutil')
            time.sleep(scitags.settings.NETSTAT_TIMEOUT)
            continue

        for entry in netc:
            if entry.status == 'LISTEN':
                continue
            prot = 'tcp'
            saddr = u'{}'.format(entry.laddr.ip)
            sport = entry.laddr.port
            daddr = u'{}'.format(entry.raddr.ip)
            dport = entry.raddr.port
            status = entry.status
            try:
                ipaddress.ip_address(saddr)
                ipaddress.ip_address(daddr)
            except ValueError as e:
                log.debug('Failed to parse IPs: {}/{}'.format(saddr, daddr))
                log.exception(e)
                continue
            netstat.add((prot, saddr, sport, daddr, dport))
            netstat_status[(prot, saddr, sport, daddr, dport)] = status
        log.debug(netstat)
        log.debug(netstat_status)

        if init_pass:
            for c in netstat:
                daddr = ipaddress.ip_address(c[3])
                if __int_ip(daddr, int_networks):
                    continue
                if not netstat_status[c] == 'ESTABLISHED':
                    continue
                f_id = scitags.FlowID('ongoing', *c + (config['NETSTAT_EXPERIMENT'], config['NETSTAT_ACTIVITY']))
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)
                init_pass = False
        if netstat_prev:
            new_connections = netstat - netstat_prev
            closed_connections = netstat_prev - netstat

            for c in new_connections:
                daddr = ipaddress.ip_address(c[3])
                if __int_ip(daddr, int_networks):
                    continue
                if not netstat_status[c] == 'ESTABLISHED':
                    continue
                f_id = scitags.FlowID('start', *c + (config['NETSTAT_EXPERIMENT'], config['NETSTAT_ACTIVITY']))
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)

            for c in closed_connections:
                daddr = ipaddress.ip_address(c[3])
                if __int_ip(daddr, int_networks):
                    continue
                f_id = scitags.FlowID('end', *c + (config['NETSTAT_EXPERIMENT'], config['NETSTAT_ACTIVITY']))
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)
            # todo: fix detection of closed sockets (requires transient store for all tracked connections)
            # for c in netstat:
            #     daddr = ipaddress.ip_address(c[3])
            #     if __int_ip(daddr, int_networks):
            #         continue
            #     if c in netstat_status.keys() and netstat_status[c] == 'TIME_WAIT':
            #         f_id = scitags.FlowID('end', *c + (config['NETSTAT_EXPERIMENT'], config['NETSTAT_ACTIVITY']))
            #         log.debug('   --> {}'.format(f_id))
            #         flow_queue.put(f_id)
            #         netstat.remove(c)
        netstat_prev = netstat

        term_event.wait(scitags.settings.NETSTAT_TIMEOUT)
