# -*- coding: utf-8 -*-

"""
jishaku.repl
~~~~~~~~~~~~

Repl-related operations and tools for Jishaku.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import discord
from discord.ext import commands

# pylint: disable=wildcard-import
from jishaku.repl.compilation import *  # noqa: F401
from jishaku.repl.inspections import all_inspections  # noqa: F401
from jishaku.repl.scope import *  # noqa: F401


def get_var_dict_from_ctx(ctx: commands.Context, prefix: str = '_'):
    """
    Returns the dict to be used in REPL for a given Context.
    """

    raw_var_dict = {
        'author': ctx.author,
        'bot': ctx.bot,
        'channel': ctx.channel,
        'ctx': ctx,
        'find': discord.utils.find,
        'get': discord.utils.get,
        'guild': ctx.guild,
        'message': ctx.message,
        'msg': ctx.message
    }

    return {f'{prefix}{k}': v for k, v in raw_var_dict.items()}
