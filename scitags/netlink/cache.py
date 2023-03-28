from pyroute2.netlink.diag import DiagSocket
from pyroute2.netlink.diag import SS_CONN
from scitags.netlink.pyroute_tcp import TCP
import logging

log = logging.getLogger('scitags')


def netlink_cache_add(flow_state, src, src_port, dst, dst_port, netlink_cache):
    try:
        with DiagSocket() as ds:
            ds.bind()
            p = TCP(sk_states=SS_CONN)
            netc = p(ds)
    except Exception as e:
        log.exception('Exception caught while querying netlink')
        return

    for entry in netc:
        if 'tcp_info' not in entry.keys():
            continue
        saddr = u'{}'.format(entry['src'])
        if '::ffff:' in saddr:
            saddr = saddr.replace('::ffff:', '')
        sport = entry['src_port']
        daddr = u'{}'.format(entry['dst'])
        if '::ffff:' in daddr:
            daddr = daddr.replace('::ffff:', '')
        dport = entry['dst_port']
        if not (saddr, sport, daddr, dport) == (src, src_port, dst, dst_port):
            continue
        prot = 'tcp'
        status = entry['tcp_info']['state']
        netlink_cache[(prot, saddr, sport, daddr, dport)] = (status, entry)


def netlink_cache_update(netlink_cache):
    if not netlink_cache:     # if cache is empty there is nothing to update
        return
    try:
        with DiagSocket() as ds:
            ds.bind()
            p = TCP(sk_states=SS_CONN)
            netc = p(ds)
    except Exception as e:
        log.exception('Exception caught while querying netlink')
        return
    for entry in netc:
        if 'tcp_info' not in entry.keys():
            continue
        saddr = u'{}'.format(entry['src'])
        if '::ffff:' in saddr:
            saddr = saddr.replace('::ffff:', '')
        sport = entry['src_port']
        daddr = u'{}'.format(entry['dst'])
        if '::ffff:' in daddr:
            daddr = daddr.replace('::ffff:', '')
        dport = entry['dst_port']
        if ('tcp', saddr, sport, daddr, dport) in netlink_cache.keys():
            status = entry['tcp_info']['state']
            netlink_cache[('tcp', saddr, sport, daddr, dport)] = (status, entry)
    # todo: cleanup - check if connections in cache are still there


def netlink_cache_del(src, src_port, dst, dst_port, netlink_cache):
    if ('tcp', src, src_port, dst, dst_port) in netlink_cache.keys():
        del netlink_cache[('tcp', src, src_port, dst, dst_port)]
