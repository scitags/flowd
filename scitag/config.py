import os
import sys
import logging

from scitag import settings

__all__ = ['config']

log = logging.getLogger('scitag')
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
log.debug("loaded configuration: %s" % config)
