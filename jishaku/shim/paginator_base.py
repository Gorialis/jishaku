# -*- coding: utf-8 -*-

"""
jishaku.paginators (non-shim dependencies)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Paginator-related tools and interfaces for Jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import typing

import discord

# emoji settings, this sets what emoji are used for PaginatorInterface

_Emoji = typing.Union[str, discord.PartialEmoji, discord.Emoji]


class EmojiSettings(typing.NamedTuple):
    """
    Emoji settings, this sets what emoji are used for PaginatorInterface
    """

    start: _Emoji
    back: _Emoji
    forward: _Emoji
    end: _Emoji
    close: _Emoji


EMOJI_DEFAULT = EmojiSettings(
    start="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
    back="\N{BLACK LEFT-POINTING TRIANGLE}",
    forward="\N{BLACK RIGHT-POINTING TRIANGLE}",
    end="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
    close="\N{BLACK SQUARE FOR STOP}",
)
