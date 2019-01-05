# -*- coding: utf-8 -*-

"""
jishaku.codeblocks
~~~~~~~~~~~~~~~~~~

Converters for detecting and obtaining codeblock content

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import re
from collections import namedtuple

from discord.ext import commands

__all__ = ('Codeblock', 'CODEBLOCK_REGEX', 'CodeblockConverter')


Codeblock = namedtuple('Codeblock', 'language content')
CODEBLOCK_REGEX = re.compile("^(?:```([A-Za-z0-9\\-\\.]*)\n)?(.+?)(?:```)?$", re.S)


class CodeblockConverter(commands.Converter):  # pylint: disable=too-few-public-methods
    """
    A converter that strips codeblock markdown if it exists.

    Returns a namedtuple of (language, content).

    :attr:`Codeblock.language` is an empty string if no language was given with this codeblock.
    It is ``None`` if the input was not a complete codeblock.
    """

    async def convert(self, ctx, argument):
        match = CODEBLOCK_REGEX.search(argument)
        if not match:
            return Codeblock(None, argument)
        return Codeblock(match.group(1), match.group(2))
