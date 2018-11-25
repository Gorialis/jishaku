# -*- coding: utf-8 -*-

"""
jishaku
~~~~~~~

A discord.py extension including useful tools for bot development and debugging.

:copyright: (c) 2018 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

__author__ = 'Gorialis'
__copyright__ = 'Copyright 2018 Devon (Gorialis) R'
__docformat__ = 'restructuredtext en'
__license__ = 'MIT'
__title__ = 'jishaku'
__version__ = '1.0.3'

# pylint: disable=wildcard-import
from jishaku.cog import *  # noqa: F401

__all__ = (
    'Jishaku',
    'setup'
)
