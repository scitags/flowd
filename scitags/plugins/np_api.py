import logging
import os
import sys
import select
import stat
import ipaddress
from datetime import datetime

import scitags
import scitags.settings
from scitags.config import config

log = logging.getLogger('scitags')


def init():
    log.debug('np_api init')
    if os.path.exists(scitags.settings.NP_API_FILE) and stat.S_ISFIFO(os.stat(scitags.settings.NP_API_FILE).st_mode):
        return
    try:
        if sys.version_info[0] < 3:
            os.mkfifo(scitags.settings.NP_API_FILE, 0o666)
        else:
            os.mkfifo(scitags.settings.NP_API_FILE, mode=0o666)
    except IOError as e:
        log.error('Unable to create command pipe {}'.format(scitags.settings.NP_API_FILE))
        sys.exit(1)


def run(flow_queue, term_event, ip_config):
    np_api_fd = os.open(scitags.settings.NP_API_FILE, os.O_RDWR | os.O_NONBLOCK)
    sp = select.poll()
    sp.register(np_api_fd, select.POLLIN | select.POLLPRI)
    while not term_event.is_set():
        try:
            tr = sp.poll(3)
            if not tr:
                continue
            np_content = os.read(np_api_fd, 65535)
        except IOError as e:
            log.exception('Failed to read command pipe {}'.format(scitags.settings.NP_API_FILE))
            term_event.wait(3)
            continue
        log.debug(np_content)
        flow_ids = np_content.decode('utf-8').splitlines()
        log.debug(flow_ids)
        for f_id in flow_ids:
            entry = f_id.strip().split(' ')
            if len(entry) != 8:
                log.error('Unable to parse flow identifier received {}'.format(entry))
                continue
            flow_state = entry[0].strip()
            proto = entry[1].strip()
            src = entry[2].strip()
            src_port = entry[3].strip()
            dst = entry[4].strip()
            dst_port = entry[5].strip()
            exp_id = entry[6].strip()
            activity_id = entry[7].strip()
            start_time = None
            end_time = None
            netlink = None
            # validation, todo: ports
            try:
                ipaddress.ip_address(src)
                ipaddress.ip_address(dst)
            except ValueError as e:
                log.debug('Failed to parse IPs: {}/{}'.format(src, dst))
                log.exception(e)
                continue
            if not all(isinstance(v, int) for v in (src_port, dst_port, exp_id, activity_id)):
                log.debug('Failed to parse integers: {}'.format((src_port, dst_port, exp_id, activity_id)))
                continue

            if 'start' in flow_state:
                start_time = datetime.utcnow().isoformat() + '+00:00'
            if 'end' in flow_state:
                end_time = datetime.utcnow().isoformat() + '+00:00'

            flow_id = scitags.FlowID(flow_state, proto, src, src_port, dst, dst_port, exp_id, activity_id,
                                     start_time, end_time, netlink)
            log.debug('   --> {}'.format(flow_id))
            flow_queue.put(flow_id)

    os.unlink(scitags.settings.NP_API_FILE)
