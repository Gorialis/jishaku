# -*- coding: utf-8 -*-

"""
jishaku.cog loadability test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import pytest


@pytest.mark.parametrize(
    ("extension_name",),
    [
        ("jishaku",),
        ("jishaku.cog",)
    ]
)
def test_loads(extension_name):
    import discord
    assert discord.__version__

    from discord.ext import commands

    bot = commands.Bot('?')

    bot.load_extension(extension_name)

    assert bot.get_cog("Jishaku")
    assert isinstance(bot.get_cog("Jishaku"), commands.Cog)

    assert bot.get_command("jsk")
    assert isinstance(bot.get_command("jsk"), commands.Command)

    bot.unload_extension(extension_name)

    assert bot.get_cog("Jishaku") is None
    assert bot.get_command("jsk") is None
