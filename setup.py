from setuptools import setup

import scitags

NAME = 'python-flowd'
VERSION = scitags.VERSION
DESCRIPTION = "Flow and Packet Marking Service"
LONG_DESCRIPTION = """
Flow and Packet Marking Service (www.scitags.org)
"""
AUTHOR = scitags.AUTHOR
AUTHOR_EMAIL = scitags.AUTHOR_EMAIL
LICENSE = "ASL 2.0"
PLATFORMS = "Any"
URL = "https://github.com/scitags/flowd"
CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: Unix",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.8",
    "Topic :: Software Development :: Libraries :: Python Modules"
]

setup(name=NAME,
      version=VERSION,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      license=LICENSE,
      platforms=PLATFORMS,
      url=URL,
      classifiers=CLASSIFIERS,
      keywords='operations python network flow packet marking',
      packages=['scitags', 'scitags.backends', 'scitags.plugins', 'scitags.stun', 'scitags.netlink'],
      #install_requires=['python-daemon', 'python2-requests', 'python2-psutil', 'systemd-python'],
      data_files=[
          ('/usr/sbin', ['sbin/flowd']),
          ('/etc/flowd', ['etc/flowd.cfg']),
          ('/usr/lib/systemd/system', ['etc/flowd.service']),
      ]
      )
