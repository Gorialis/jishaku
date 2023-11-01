# -*- coding: utf-8 -*-

"""
jishaku.meta
~~~~~~~~~~~~

Meta information about jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import typing

__all__ = (
    '__author__',
    '__copyright__',
    '__docformat__',
    '__license__',
    '__title__',
    '__version__',
    'version_info'
)


class VersionInfo(typing.NamedTuple):
    """Version info named tuple for Jishaku"""
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


version_info = VersionInfo(major=2, minor=5, micro=2, releaselevel='final', serial=0)

__author__ = 'Gorialis'
__copyright__ = 'Copyright 2021 Devon (Gorialis) R'
__docformat__ = 'restructuredtext en'
__license__ = 'MIT'
__title__ = 'jishaku'
__version__ = '.'.join(map(str, (version_info.major, version_info.minor, version_info.micro)))
