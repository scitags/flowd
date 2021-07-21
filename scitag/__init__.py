import collections

AUTHOR = "Marian Babik <Marian.Babik@cern.ch>, "
AUTHOR_EMAIL = "<net-wg-dev@cern.ch>"
COPYRIGHT = "Copyright (C) 2021"
VERSION = "0.0.1"
DATE = "13 Jul 2021"
__author__ = AUTHOR
__version__ = VERSION
__date__ = DATE


class FlowConfigException(Exception):
    pass


# Flow Identifier
# flow-start
#   inputs: (protocol, src, src_port, dst, dst_port, experiment, activity)
# flow-end
#   inputs: (protocol, src, src_port, dst, dst_port, experiment, activity)
# flow-update (optional)
#   inputs: (protocol, src, src_port, dst, dst_port, experiment, activity)
FlowID = collections.namedtuple('FlowID', ['state', 'prot', 'src', 'src_port', 'dst', 'dst_port', 'exp', 'act'])
