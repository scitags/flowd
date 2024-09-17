import logging
import re

from scitags.config import config
import scitags.settings

try:
    import subprocess32 as subprocess
except ImportError:
    import subprocess

try:
    from subprocess import STDOUT, check_output, CalledProcessError
except ImportError:
    STDOUT = subprocess.STDOUT

    def check_output(*popenargs, **kwargs):
        if 'stdout' in kwargs:  # pragma: no cover
            raise ValueError('stdout argument not allowed, it will be overridden.')
        if 'timeout' in kwargs:
            timeout = kwargs['timeout']
            del kwargs['timeout']
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, _ = process.communicate(timeout=timeout)
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd, output=output)
        return output
    subprocess.check_output = check_output
    # overwrite CalledProcessError due to `output`
    # keyword not being available (in 2.6)


    class CalledProcessError(Exception):
        def __init__(self, returncode, cmd, output=None):
            self.returncode = returncode
            self.cmd = cmd
            self.output = output

        def __str__(self):
            return "Command '%s' returned non-zero exit status %d" % (
                self.cmd, self.returncode)
    subprocess.CalledProcessError = CalledProcessError

log = logging.getLogger('scitags')

SKMEM = ('rmem_alloc', 'rcv_buf', 'wmem_allow', 'snd_buf', 'fwd_alloc', 'wmem_queued', 'opt_mem', 'back_log',
         'sock_drop')

TCP_STATES = {'ESTAB': "established",
              'SYN-SENT': "syn-sent",
              'SYN-RECV': "syn-recv",
              'FIN-WAIT-1': "fin-wait-1",
              'FIN-WAIT-2': "fin-wait-2",
              'TIME-WAIT': "time-wait",
              'UNCONN': "unconnected",
              'CLOSE-WAIT': "close-wait",
              'LAST-ACK': "last-ack",
              'LISTEN': "listening",
              'CLOSING': "closing"}


def ss(ss_path='/sbin/ss'):

    try:
        str_out = subprocess.check_output(ss_path+' -iotnmH', shell=True, stderr=subprocess.STDOUT, stdin=None,
                                          timeout=5)
    except subprocess.TimeoutExpired as e:
        log.exception(e)
        return
    except subprocess.CalledProcessError as e:
        str_out = e.output
    return str_out


def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return zip(a, a)


def parse_ip(hdrs):
    src_raw = hdrs[3]
    dst_raw = hdrs[4]
    src_zone = re.search(r'.*(%vlan.*\d+):.*', src_raw)
    dst_zone = re.search(r'.*(%vlan.*\d+):.*', dst_raw)
    if src_zone:
        src_raw = src_raw.replace(src_zone.group(1), "")
    if dst_zone:
        dst_raw = dst_raw.replace(dst_zone.group(1), "")
    if '[' in src_raw:  # ipv6
        src_t = src_raw.split(']:')
        dst_t = dst_raw.split(']:')
        src = src_t[0][1:]
        dst = dst_t[0][1:]
        src_port = src_t[1]
        dst_port = dst_t[1]
    else:               # ipv4
        src = src_raw.split(':')[0]
        dst = dst_raw.split(':')[0]
        src_port = src_raw.split(':')[1]
        dst_port = dst_raw.split(':')[1]

    if '::ffff:' in src:   # ip4 in ip6
        src = src.replace('::ffff:', '')
    if '::ffff:' in dst_raw:
        dst = dst.replace('::ffff:', '')

    return src, src_port, dst, dst_port


def num(s):
    s = s.replace('bps', '').replace('M', '').replace('K', '')
    if not re.fullmatch('(\d+(?:\.\d+)?)', s):
        return 0
    try:
        return int(s)
    except ValueError:
        return float(s)


def parse_ss(ss_stdout):
    log.debug('parse_ss')
    netc = list()
    ss_lines = ss_stdout.splitlines()
    for hdr, tcp_info in pairwise(ss_lines):
        netc_entry = dict()
        try:
            hdrs = hdr.decode('utf-8').split()
            # ignore localhost connections
            if '[::1]' in hdrs[3] or '[::1]' in hdrs[4]:
                continue
            (src, src_port, dst, dst_port) = parse_ip(hdrs)
            netc_entry['src'] = src
            netc_entry['dst'] = dst
            netc_entry['src_port'] = int(src_port)
            netc_entry['dst_port'] = int(dst_port)
            if hdrs[0] and hdrs[0] in TCP_STATES.keys():
                tcp_state = TCP_STATES[hdrs[0]]
            else:
                tcp_state = 'unknown'
        except Exception as e:
            log.exception(e)
            continue
        tcpi = tcp_info.decode('utf-8').strip().split()
        tcpi_entry = dict()
        tcpi_entry['opts'] = list()
        tcpi_entry['state'] = tcp_state
        for e in tcpi:
            if 'bbr:(' in e:
                bbr_raw = e.replace('bbr:(', '')[:-1].split(',')
                for be in bbr_raw:
                    tcpi_entry['bbr_'+be.split(':')[0]] = num(be.split(':')[1])
            elif 'skmem:(' in e:
                skmem_raw = e.replace('skmem:(', '')[:-1].split(',')
                if len(skmem_raw) != 9:
                    continue
                for skh, ske in zip(SKMEM, skmem_raw):
                    tcpi_entry['skmem_'+skh] = num(re.sub('\D', '', ske))
            elif re.match(r'^rtt:*.', e):
                rem = re.findall(r'^rtt:(\d+\.\d+)/(\d+\.\d+)$', e)
                if rem and len(rem[0]) == 2:
                    tcpi_entry['rtt'] = num(rem[0][0])
                    tcpi_entry['rtt_var'] = num(rem[0][1])
            elif 'rwnd_limited:' in e:
                tcpi_entry['rwnd_limited'] = num(e.split(':')[1].split('(')[0].replace('ms', ''))
            elif 'sndbuf_limited:' in e:
                tcpi_entry['sndbuf_limited'] = num(e.split(':')[1].split('(')[0].replace('ms', ''))
            elif 'wscale' in e:
                tcpi_entry['opts'].append(e)
            elif ':' in e:
                k, v = e.split(':')
                v = v.replace('ms', '')
                if '.' in v:
                    tcpi_entry[k] = num(v)
                elif ',' in v:
                    tcpi_entry[k] = v
                elif '/' in v:
                    tcpi_entry[k] = num(v.split('/')[1])
                elif v:
                    tcpi_entry[k] = num(v)
                else:
                    tcpi_entry[k] = v
            elif 'rate' in e:
                print(tcpi[tcpi.index(e)+1])
                tcpi_entry[e] = num(tcpi[tcpi.index(e)+1])
            elif e == 'send':
                tcpi_entry['send'] = num(tcpi[tcpi.index(e)+1])
            elif 'bps' not in e and 'app_limited' not in e:
                tcpi_entry['opts'].append(e)
        netc_entry['tcp_info'] = tcpi_entry
        netc.append(netc_entry)
    return netc


def netlink_cache_add(flow_state, src, src_port, dst, dst_port, netlink_cache):
    try:
        ss_path = config.get('PROMETHEUS_SS_PATH', scitags.settings.SS_PATH)
        netc = parse_ss(ss(ss_path=ss_path))
    except Exception as e:
        log.exception('Exception caught while querying netlink')
        return

    for entry in netc:
        if 'tcp_info' not in entry.keys():
            continue
        saddr = u'{}'.format(entry['src'])
        sport = entry['src_port']
        daddr = u'{}'.format(entry['dst'])
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
        ss_path = config.get('PROMETHEUS_SS_PATH', scitags.settings.SS_PATH)
        netc = parse_ss(ss(ss_path=ss_path))
    except Exception as e:
        log.exception('Exception caught while querying netlink')
        return
    for entry in netc:
        if 'tcp_info' not in entry.keys():
            continue
        saddr = u'{}'.format(entry['src'])
        sport = entry['src_port']
        daddr = u'{}'.format(entry['dst'])
        dport = entry['dst_port']
        if ('tcp', saddr, sport, daddr, dport) in netlink_cache.keys():
            status = entry['tcp_info']['state']
            netlink_cache[('tcp', saddr, sport, daddr, dport)] = (status, entry)
    # todo: cleanup - check if connections in cache are still there


def netlink_cache_del(src, src_port, dst, dst_port, netlink_cache):
    if ('tcp', src, src_port, dst, dst_port) in netlink_cache.keys():
        del netlink_cache[('tcp', src, src_port, dst, dst_port)]
