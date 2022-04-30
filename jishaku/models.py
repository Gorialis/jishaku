# -*- coding: utf-8 -*-

"""
jishaku.models
~~~~~~~~~~~~~~

Functions for modifying or interfacing with discord.py models.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import copy
import typing

import discord

from jishaku.types import ContextT


async def copy_context_with(
    ctx: ContextT,
    *,
    author: typing.Optional[typing.Union[discord.Member, discord.User]] = None,
    channel: typing.Optional[discord.TextChannel] = None,
    **kwargs: typing.Any
) -> ContextT:
    """
    Makes a new :class:`Context` with changed message properties.
    """

    # copy the message and update the attributes
    alt_message: discord.Message = copy.copy(ctx.message)
    alt_message._update(kwargs)  # type: ignore # pylint: disable=protected-access

    if author is not None:
        alt_message.author = author
    if channel is not None:
        alt_message.channel = channel

    # obtain and return a context of the same type
    return await ctx.bot.get_context(alt_message, cls=type(ctx))
