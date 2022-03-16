# -*- coding: utf-8 -*-

"""
jishaku subclassing test 2
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a valid extension file for discord.py intended to
discover weird behaviors related to subclassing.

This variant overrides behavior directly.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect

from discord.ext import commands

import jishaku


class Magnet2(*jishaku.OPTIONAL_FEATURES, *jishaku.STANDARD_FEATURES):  # pylint: disable=too-few-public-methods
    """
    The extended Jishaku cog
    """

    @jishaku.Feature.Command(name="jishaku", aliases=["jsk"], invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: commands.Context):
        """
        override test
        """
        return await ctx.send("The behavior of this command has been overridden directly.")


async def async_setup(bot: commands.Bot):
    """
    The async setup function for the extended cog
    """

    await bot.add_cog(Magnet2(bot=bot))


def setup(bot: commands.Bot):
    """
    The setup function for the extended cog
    """

    if inspect.iscoroutinefunction(bot.add_cog):
        return async_setup(bot)
    else:
        bot.add_cog(Magnet2(bot=bot))
