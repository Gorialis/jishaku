# -*- coding: utf-8 -*-

"""
jishaku.meta
~~~~~~~~~~~~

Meta information about jishaku.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

from collections import namedtuple

__all__ = (
    '__author__',
    '__copyright__',
    '__docformat__',
    '__license__',
    '__title__',
    '__version__',
    'version_info'
)

__author__ = 'Gorialis'
__copyright__ = 'Copyright 2019 Devon (Gorialis) R'
__docformat__ = 'restructuredtext en'
__license__ = 'MIT'
__title__ = 'jishaku'
__version__ = '1.16.7'

# pylint: disable=invalid-name
VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')
version_info = VersionInfo(major=1, minor=16, micro=7, releaselevel='final', serial=0)
