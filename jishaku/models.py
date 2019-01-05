# -*- coding: utf-8 -*-

"""
jishaku.models
~~~~~~~~~~~~~~

Functions for modifying or interfacing with discord.py models.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import copy

from discord.ext import commands


async def copy_context_with(ctx: commands.Context, *, author=None, **kwargs):
    """
    Makes a new :class:`Context` with changed message properties.
    """

    # copy the message and update the attributes
    alt_message = copy.copy(ctx.message)
    alt_message._update(alt_message.channel, kwargs)  # pylint: disable=protected-access

    if author is not None:
        alt_message.author = author

    # obtain and return a context of the same type
    return await ctx.bot.get_context(alt_message, cls=type(ctx))
