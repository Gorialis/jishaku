# -*- coding: utf-8 -*-

"""
jishaku.repl
~~~~~~~~~~~~

Repl-related operations and tools for Jishaku.

:copyright: (c) 2018 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

from discord.ext import commands

# pylint: disable=wildcard-import
from jishaku.repl.compilation import *  # noqa: F401
from jishaku.repl.inspections import all_inspections  # noqa: F401
from jishaku.repl.scope import *  # noqa: F401


def get_var_dict_from_ctx(ctx: commands.Context):
    """
    Returns the dict to be used in REPL for a given Context.
    """

    return {
        '_author': ctx.author,
        '_bot': ctx.bot,
        '_channel': ctx.channel,
        '_ctx': ctx,
        '_guild': ctx.guild,
        '_message': ctx.message,
        '_msg': ctx.message
    }
