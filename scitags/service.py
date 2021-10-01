import datetime
import logging
import importlib
import os
import pkgutil
import sys
import multiprocessing as mp

try:
    import queue
except ImportError:
    import Queue as queue
import signal
import requests
import json

import scitags
import scitags.settings
import scitags.plugins
import scitags.backends
import scitags.stun.services
from scitags.config import config

log = logging.getLogger('scitags')


class FlowService(object):
    def __init__(self, args):
        self.backend = config.get('BACKEND')
        self.backend_mod = None
        self.backend_proc = None
        self.plugin = config.get('PLUGIN')
        self.plugin_mod = None
        self.plugin_proc = None
        if args.debug or args.fg:
            self.debug = True
        else:
            self.debug = False
        self.flow_id_queue = mp.Queue()
        self.term_event = mp.Event()

        header = list()
        header.append("Flow and Packet Marking Service (scitags.org)")
        header.append("flowd v.{}: {}".format(scitags.__version__, datetime.datetime.now()))
        header.append("config: {}".format(scitags.settings.CONFIG_PATH))
        l_max = len(max(header, key=lambda x: len(x)))
        log.info('*' * (l_max + 4))
        for line in header:
            log.info('* {0:<{1}s} *'.format(line, l_max))
        log.info('*' * (l_max + 4))

        if 'IP_DISCOVERY_ENABLED' in config.keys() and config['IP_DISCOVERY_ENABLED']:
            try:
                eip4, iip4, eip6, iip6 = scitags.stun.services.get_ext_ip()
                log.info('network info:')
                log.info('              {}/{}'.format(iip4, eip4))
                log.info('              {}/{}'.format(iip6, eip6))
                self.ip_config = scitags.IPConfig(eip4, iip4, eip6, iip6)
            except Exception as e:
                log.exception(e)
                sys.exit(1)
        else:
            self.ip_config = None

        flow_api = requests.get(config['FLOW_MAP_API'], verify=False)
        if flow_api.status_code != 200:
            log.error('Failed to access FLOW MAP API at {} got {}'.format(config.FLOW_MAP_API, flow_api.status_code))
            sys.exit(1)
        try:
            # self.flow_map stores flow_id lookup dict; e.g.
            # 'experiments': {u'atlas': 16, ..}
            # 'activities': {16: {u'rebalancing': 16, u'production': 14}, etc.
            self.flow_map = dict()
            flow_map_raw = json.loads(flow_api.content)
            self.flow_map['experiments'] = dict()
            self.flow_map['activities'] = dict()
            for exp in flow_map_raw['experiments']:
                self.flow_map['experiments'][exp['expName']] = exp['expId']
                self.flow_map['activities'][exp['expId']] = dict()
                for act in exp['activities']:
                    self.flow_map['activities'][exp['expId']][act['activityName']] = act['activityId']
            log.debug('flow map loaded')
            log.debug(self.flow_map)
        except Exception as e:
            log.exception('Failed to parse FLOW MAP API')
            sys.exit(1)
        log.info('flow map registry loaded')

    def init_plugins(self):
        log.debug("    Loading plugin {}".format(self.plugin))
        try:
            default_pkg = os.path.dirname(scitags.plugins.__file__)
            if self.plugin in [name for _, name, _ in pkgutil.iter_modules([default_pkg])]:
                if sys.version_info[0] < 3:
                    self.plugin_mod = __import__("scitags.plugins.{}".format(self.plugin), globals(), locals(),
                                                 [self.plugin])
                else:
                    self.plugin_mod = importlib.import_module("scitags.plugins.{}".format(self.plugin))
            else:
                log.error("Configured plugin not found")
                return False
        except ImportError as e:
            log.exception(e)
            log.error("Exception caught {} while loading plugin {}".format(e, self.plugin))
            sys.exit(1)

        try:
            log.debug("    Calling plugin init: {}".format(self.plugin))
            self.plugin_mod.init()
        except Exception as e:
            log.exception(e)
            log.error("Exception was thrown while initialing plugin {} ({})".format(self.plugin, e))
            sys.exit(1)
        log.info('plugin loaded: {}'.format(self.plugin))

        backend = config.get('BACKEND', scitags.settings.DEFAULT_BACKEND)
        log.debug("    Loading backend {}".format(backend))
        try:
            default_pkg = os.path.dirname(scitags.backends.__file__)
            if self.backend in [name for _, name, _ in pkgutil.iter_modules([default_pkg])]:
                if sys.version_info[0] < 3:
                    self.backend_mod = __import__("scitags.backends.{}".format(self.backend), globals(), locals(),
                                                  [self.backend])
                else:
                    self.backend_mod = importlib.import_module("scitags.backends.{}".format(self.backend))
            else:
                log.error("Configured backend not found")
                return False
        except ImportError as e:
            log.error("Exception caught {} while loading backend {}".format(e, self.backend))
            sys.exit(1)
        log.info('backend loaded: {}'.format(self.backend))

    def cleanup(self, sig, frame):
        log.info('caught signal {}'.format(sig))
        self.term_event.set()

        while True:
            try:
                self.flow_id_queue.get(block=False)
            except queue.Empty:
                break
            except ValueError:
                break
        self.flow_id_queue.close()
        self.flow_id_queue.join_thread()

        if self.plugin_proc and self.plugin_proc.is_alive():
            self.plugin_proc.join(5)

        if self.backend_proc and self.backend_proc.is_alive():
            self.backend_proc.join(5)

        # wait -> if self.plugin_proc.is_alive()
        # self.plugin_proc.terminate()
        if sys.version_info[0] < 3:
            pass
        else:
            self.plugin_proc.close()
            self.backend_proc.close()
        if os.path.isfile(scitags.settings.PID_FILE):
            os.remove(scitags.settings.PID_FILE)
        log.info('cleanup done')

    @staticmethod
    def reload_config():
        if sys.version_info[0] < 3:
            reload(scitags.config)
        else:
            importlib.reload(scitags.config)

    def main(self):
        # 1. create queue and process pool for backend
        # 2. create process or pool for plugin
        # 3. watch plugin and backend pools until they finish
        log.info('entering main loop')
        self.backend_proc = mp.Process(target=self.backend_mod.run,
                                       args=(self.flow_id_queue, self.term_event, self.flow_map, self.ip_config))
        self.backend_proc.daemon = True
        self.plugin_proc = mp.Process(target=self.plugin_mod.run,
                                      args=(self.flow_id_queue, self.term_event, self.ip_config))
        self.plugin_proc.daemon = True

        try:
            self.backend_proc.start()
            self.plugin_proc.start()
            if self.debug:
                signal.signal(signal.SIGINT, self.cleanup)
                signal.signal(signal.SIGTERM, self.cleanup)
            self.plugin_proc.join()
        except Exception as e:
            log.exception('Exception caught in main')
        log.info('flowd terminated')
