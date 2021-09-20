import os
import sys
import logging

from scitags import settings

__all__ = ['config']

log = logging.getLogger('scitags')
_bcf = settings.CONFIG_PATH

if not os.path.exists(_bcf):
    log.error("Config error {}".format(settings.CONFIG_PATH))
    sys.exit(1)

config = {}
if sys.version_info[0] == 2:
    execfile(_bcf, {}, config)
else:
    with open(_bcf) as f:
        code = compile(f.read(), os.path.basename(_bcf), 'exec')
        exec(code, {}, config)
log.info("configuration loaded")
log.debug("config: {}".format(config))

