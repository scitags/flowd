import datetime
import logging
import fcntl
import importlib
import os
import pkgutil
import sys
import multiprocessing as mp
import queue
import signal

import scitag
import scitag.settings
import scitag.plugins
import scitag.backends
import scitag.stun.services
from scitag.config import config


log = logging.getLogger('scitag')


def unlock_file(f):
    if f.writable():
        fcntl.lockf(f, fcntl.LOCK_UN)


class FlowService(object):
    def __init__(self, args, pid_file):
        self.pid_file = pid_file
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
        header.append("flowd v.{}: {}".format(scitag.__version__, datetime.datetime.now()))
        header.append("config: {}".format(scitag.settings.CONFIG_PATH))
        l_max = len(max(header, key=lambda x: len(x)))
        log.info('*' * (l_max + 4))
        for line in header:
            log.info('* {0:<{1}s} *'.format(line, l_max))
        log.info('*' * (l_max + 4))

        if 'IP_DISCOVERY_ENABLED' in config.keys() and config['IP_DISCOVERY_ENABLED']:
            try:
                eip, iip = scitag.stun.services.get_ext_ip()
                log.info('network info: {}/{}'.format(iip, eip))
            except Exception as e:
                log.exception(e)
                sys.exit(1)

    def init_plugins(self):
        log.debug("    Loading plugin {}".format(self.plugin))
        try:
            default_pkg = os.path.dirname(scitag.plugins.__file__)
            if self.plugin in [name for _, name, _ in pkgutil.iter_modules([default_pkg])]:
                self.plugin_mod = importlib.import_module("scitag.plugins.{}".format(self.plugin))
            else:
                log.error("Configured plugin not found")
                return False
        except ImportError as e:
            log.error("Exception caught {} while loading plugin {}".format(e, self.plugin))
            sys.exit(1)

        try:
            log.debug("    Calling plugin init: {}".format(self.plugin))
            self.plugin_mod.init()
        except Exception as e:
            log.error("Exception was thrown while initialing plugin {} ({})".format(self.plugin, e))
            sys.exit(1)

        backend = config.get('BACKEND', scitag.settings.DEFAULT_BACKEND)
        log.debug("    Loading backend {}".format(backend))
        try:
            default_pkg = os.path.dirname(scitag.backends.__file__)
            if self.backend in [name for _, name, _ in pkgutil.iter_modules([default_pkg])]:
                self.backend_mod = importlib.import_module("scitag.backends.{}".format(self.backend))
            else:
                log.error("Configured backend not found")
                return False
        except ImportError as e:
            log.error("Exception caught {} while loading backend {}".format(e, self.backend))
            sys.exit(1)

    def cleanup(self, sig, frame):
        log.debug('caught signal {}'.format(sig))
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
        self.plugin_proc.close()
        self.backend_proc.close()
        unlock_file(self.pid_file)
        log.debug('cleanup done ... ')

    @staticmethod
    def reload_config():
        importlib.reload(scitag.config)

    def main(self):
        # 1. create queue and process pool for backend
        # 2. create process or pool for plugin
        # 3. watch plugin and backend pools until they finish
        self.backend_proc = mp.Process(target=self.backend_mod.run,
                                       args=(self.flow_id_queue, self.term_event),
                                       daemon=True)
        self.plugin_proc = mp.Process(target=self.plugin_mod.run,
                                      args=(self.flow_id_queue, self.term_event),
                                      daemon=True)

        try:
            self.backend_proc.start()
            self.plugin_proc.start()
            if self.debug:
                signal.signal(signal.SIGINT, self.cleanup)
                signal.signal(signal.SIGTERM, self.cleanup)
            self.plugin_proc.join()
        except Exception as e:
            log.exception('Exception caught in main')
        log.debug('flowd terminated')
