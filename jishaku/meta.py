# -*- coding: utf-8 -*-

"""
jishaku.meta
~~~~~~~~~~~~

Meta information about jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

from collections import namedtuple

import pkg_resources

__all__ = (
    '__author__',
    '__copyright__',
    '__docformat__',
    '__license__',
    '__title__',
    '__version__',
    'version_info'
)

# pylint: disable=invalid-name
VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')
version_info = VersionInfo(major=2, minor=3, micro=0, releaselevel='final', serial=0)

__author__ = 'windozo111'
__copyright__ = 'Copyright 2021 Devon (Gorialis) R'
__docformat__ = 'restructuredtext en'
__license__ = 'MIT'
__title__ = 'jishaku'
__version__ = '.'.join(map(str, (version_info.major, version_info.minor, version_info.micro)))

<<<<<<< Updated upstream:jishaku/meta.py
# This ensures that when jishaku is reloaded, pkg_resources requeries it to provide correct version info
pkg_resources.working_set.by_key.pop('jishaku', None)
=======
# This ensures that when gishaku is reloaded, pkg_resources requeries it to provide correct version info
pkg_resources.working_set.by_key.pop('gishaku', None)
>>>>>>> Stashed changes:gishaku/meta.py
