import logging
import time
import psutil
import ipaddress
import pprint
from datetime import datetime
import random

import scitags
import scitags.settings
from scitags.config import config

log = logging.getLogger('scitags')

# ATLAS Analysis Download 65572 exp_id=2 act_id=9
# ATLAS Production Download 65612 exp_id=2 act_id=19
# CMS Cache 196620 exp_id=3 act_id=3
# CMS DataChallenge 196624 exp_id=3 act_id=4
# LHCb Cache 32780 exp_id=4 act_id=3
# LHCb DataChallenge 32784 exp_id=4 act_id=4
# ALICE Data Access 163880 exp_id=5 act_id=10
# ALICE CLI Download 163896 exp_id=5 act_id=14

FLOW_IDS = [(2, 9), (2, 19), (3, 3), (3, 4), (4, 3), (4, 4), (5, 10), (5, 14)]

def init():
    log.debug('init')
    if 'NETSTAT_INTERNAL_NETWORKS' in config.keys():
        for net in config['NETSTAT_INTERNAL_NETWORKS']:
            try:
                ipaddress.ip_network(u'{}'.format(net))
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
    netstat_index = dict()
    int_networks = set()
    init_pass = True
    if 'NETSTAT_INTERNAL_NETWORKS' in config.keys():
        for net in config['NETSTAT_INTERNAL_NETWORKS']:
            int_networks.add(ipaddress.ip_network(u'{}'.format(net)))

    while not term_event.is_set():
        netstat = dict()
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
            netstat[(prot, saddr, sport, daddr, dport)] = status

        if init_pass:
            # register existing connections - don't trigger any fireflies as
            # we don't have start_time for them
            init_pass = False
            for k, v in netstat.items():
                daddr = ipaddress.ip_address(k[3])
                if __int_ip(daddr, int_networks):
                    continue
                netstat_index[k] = dict()
                netstat_index[k]['status'] = v
                netstat_index[k]['start_time'] = None
                netstat_index[k]['end_time'] = None
                time.sleep(scitags.settings.NETSTAT_TIMEOUT)
                continue

        for k, v in netstat.items():
            daddr = ipaddress.ip_address(k[3])
            if __int_ip(daddr, int_networks):
                continue
            if k not in netstat_index.keys() and v == 'ESTABLISHED':
                netstat_index[k] = dict()
                netstat_index[k]['status'] = v
                netstat_index[k]['start_time'] = datetime.utcnow().isoformat()+'+00:00'
                netstat_index[k]['end_time'] = None
                fl_id_index = random.randint(0, len(FLOW_IDS)-1)
                exp, act = FLOW_IDS[fl_id_index]
                netstat_index[k]['exp'] = exp
                netstat_index[k]['act'] = act
                f_id = scitags.FlowID('start', *k + (exp, act, netstat_index[k]['start_time']))
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)
            elif k in netstat_index.keys() and v in ['TIME_WAIT', 'LAST_ACK', 'FIN_WAIT1', 'FIN_WAIT2', 'CLOSING',
                                                     'CLOSE_WAIT', 'CLOSED']:
                if netstat_index[k]['end_time']:   # end_time set indicates firefly was sent already
                    continue
                if not netstat_index[k]['start_time']:   # start_time not set indicates it pre-dates flowd (init_pass)
                    continue
                netstat_index[k]['end_time'] = datetime.utcnow().isoformat()+'+00:00'
                f_id = scitags.FlowID('end', *k + (netstat_index[k]['exp'], netstat_index[k]['act'],
                                                   netstat_index[k]['start_time'], netstat_index[k]['end_time']))
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)

        # cleanup
        closed_connections = set(netstat_index.keys()) - set(netstat.keys())
        if closed_connections:
            log.debug("  closed: {}".format(closed_connections))
        for c in closed_connections:
            # connections where we didn't catch end state ?
            if netstat_index[c]['start_time'] and not netstat_index[c]['end_time']:
                netstat_index[c]['end_time'] = datetime.utcnow().isoformat() + '+00:00'
                f_id = scitags.FlowID('end', *c + (netstat_index[c]['exp'], netstat_index[c]['act'],
                                                   netstat_index[c]['start_time'], netstat_index[c]['end_time']))
                log.debug('   --> {}'.format(f_id))
                flow_queue.put(f_id)
            netstat_index.pop(c, None)
        for k, v in netstat_index.items():
            if not netstat_index[k]['start_time'] or not netstat_index[k]['end_time']:
                continue
            log.debug("  netstat_index: {} -> {}".format(k, v))

        term_event.wait(scitags.settings.NETSTAT_TIMEOUT)
