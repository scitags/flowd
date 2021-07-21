import logging
import os
import sys
import select
import stat

import scitag
import scitag.settings
from scitag.config import config

log = logging.getLogger('scitag')


def init():
    log.debug('np_api init')
    if os.path.exists(scitag.settings.NP_API_FILE) and stat.S_ISFIFO(os.stat(scitag.settings.NP_API_FILE).st_mode):
        return
    try:
        os.mkfifo(scitag.settings.NP_API_FILE, mode=0o666)
    except IOError as e:
        log.error('Unable to create command pipe {}'.format(scitag.settings.NP_API_FILE))
        sys.exit(1)


def run(flow_queue, term_event):
    np_api_fd = os.open(scitag.settings.NP_API_FILE, os.O_RDWR | os.O_NONBLOCK)
    sp = select.poll()
    sp.register(np_api_fd, select.POLLIN | select.POLLPRI)
    while not term_event.is_set():
        try:
            tr = sp.poll(3)
            if not tr:
                continue
            np_content = os.read(np_api_fd, 65535)
        except IOError as e:
            log.exception('Failed to read command pipe {}'.format(scitag.settings.NP_API_FILE))
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
            # todo: validate entries
            flow_id = scitag.FlowID(entry[0].strip(), entry[1].strip(), entry[2].strip(), entry[3].strip(),
                                    entry[4].strip(), entry[5].strip(), entry[6].strip(), entry[7].strip())
            log.debug('   --> {}'.format(flow_id))
            flow_queue.put(flow_id)

    os.unlink(scitag.settings.NP_API_FILE)
