from setuptools import setup

import scitag

NAME = 'python-flowd'
VERSION = scitag.VERSION
DESCRIPTION = "Flow and Packet Marking Daemon"
LONG_DESCRIPTION = """
Flow and Packet Marking Service (www.scitag.org)
"""
AUTHOR = scitag.AUTHOR
AUTHOR_EMAIL = scitag.AUTHOR_EMAIL
LICENSE = "ASL 2.0"
PLATFORMS = "Any"
URL = "https://github.com/sci-tag/flowd"
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
      packages=['scitag'],
      install_requires=[],
      data_files=[
          ('/usr/sbin', ['sbin/flowd']),
      ]
      )
