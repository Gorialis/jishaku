# -*- coding: utf-8 -*-

"""
Jishaku
~~~~~~~

A debugging, testing and experimentation cog for Discord bots.

:copyright: (c) 2017 Devon R
:license: MIT, see LICENSE for more details.

"""

__title__ = 'jishaku'
__author__ = 'Gorialis'
__license__ = 'MIT'
__copyright__ = 'Copyright 2017 Devon R'
__version__ = '0.1.0'


from . import cog


def setup(bot):
    """
    Loads the cog into a bot, if the module was used as an extension.
    """
    bot.add_cog(cog.Jishaku(bot))
