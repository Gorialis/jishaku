# -*- coding: utf-8 -*-

__version__ = '0.0.2'

from . import cog


def setup(bot):
    bot.add_cog(cog.Jishaku(bot))
