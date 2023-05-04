from setuptools import setup

import scitags

NAME = 'flowd'
VERSION = scitags.VERSION
DESCRIPTION = "Flow and Packet Marking Service"
LONG_DESCRIPTION = """
Flow and Packet Marking Service (flowd) implementation based on the SciTags specification (www.scitags.org).
"""
AUTHOR = scitags.AUTHOR
AUTHOR_EMAIL = scitags.AUTHOR_EMAIL
LICENSE = "ASL 2.0"
PLATFORMS = "Any"
URL = "https://github.com/scitags/flowd"
CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Topic :: Scientific/Engineering",
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
      download_url='https://github.com/scitags/flowd/archive/refs/tags/{}.tar.gz'.format(VERSION),
      classifiers=CLASSIFIERS,
      python_requires=">=3.5",
      keywords='operations python network flow packet marking',
      packages=['scitags',
                'scitags.backends',
                'scitags.plugins',
                'scitags.stun',
                'scitags.netlink'],
      install_requires=['psutil',
                        'requests',
                        'prometheus_client'],
      data_files=[
          ('/usr/sbin', ['sbin/flowd']),
          ('/etc/flowd', ['etc/flowd.cfg']),
          ('/usr/lib/systemd/system', ['etc/flowd.service']),
      ])
