# -*- coding: utf-8 -*-

"""
jishaku.cog loadability test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import unittest


class LoadabilityTest(unittest.TestCase):
    def test_loads(self):
        import discord
        self.assertTrue(discord.__version__)

        from discord.ext import commands

        bot = commands.Bot('?')

        bot.load_extension("jishaku")
        bot.unload_extension("jishaku")

        bot.load_extension("jishaku.cog")
        bot.unload_extension("jishaku.cog")
