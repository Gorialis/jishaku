# -*- coding: utf-8 -*-

"""
jishaku.types
~~~~~~~~~~~~~

Declarations for type checking

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import typing

import discord
from discord.ext import commands

BotT = typing.Union[commands.Bot, commands.AutoShardedBot]

if typing.TYPE_CHECKING or discord.version_info >= (2, 0, 0):
    ContextT = typing.TypeVar('ContextT', commands.Context[commands.Bot], commands.Context[commands.AutoShardedBot])
    ContextA = commands.Context[BotT]
else:
    ContextT = ContextA = commands.Context
