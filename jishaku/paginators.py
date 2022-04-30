# -*- coding: utf-8 -*-

"""
jishaku.paginators
~~~~~~~~~~~~~~~~~~

Paginator-related tools and interfaces for Jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import typing

import discord
from discord.ext import commands

from jishaku.flags import Flags
from jishaku.hljs import get_language, guess_file_traits
from jishaku.shim.paginator_base import EmojiSettings
from jishaku.types import ContextA

# Version detection
if discord.version_info >= (2, 0, 0):
    from jishaku.shim.paginator_200 import PaginatorEmbedInterface, PaginatorInterface
else:
    from jishaku.shim.paginator_170 import PaginatorEmbedInterface, PaginatorInterface

__all__ = ('EmojiSettings', 'PaginatorInterface', 'PaginatorEmbedInterface',
           'WrappedPaginator', 'FilePaginator', 'use_file_check')


class WrappedPaginator(commands.Paginator):
    """
    A paginator that allows automatic wrapping of lines should they not fit.

    This is useful when paginating unpredictable output,
    as it allows for line splitting on big chunks of data.

    Delimiters are prioritized in the order of their tuple.

    Parameters
    -----------
    wrap_on: tuple
        A tuple of wrapping delimiters.
    include_wrapped: bool
        Whether to include the delimiter at the end of a wrapped line.
    force_wrap: bool
        If this is True, lines will be split at their maximum points should trimming not be possible
        with any provided delimiter.
    """

    def __init__(
        self,
        *args: typing.Any,
        wrap_on: typing.Tuple[str, ...] = ('\n', ' '),
        include_wrapped: bool = True,
        force_wrap: bool = False,
        **kwargs: typing.Any
    ):
        super().__init__(*args, **kwargs)
        self.wrap_on = wrap_on
        self.include_wrapped = include_wrapped
        self.force_wrap = force_wrap

    def add_line(self, line: str = '', *, empty: bool = False):
        true_max_size = self.max_size - self._prefix_len - self._suffix_len - 2 * self._linesep_len
        start = 0
        needle = 0
        last_delimiter = -1
        last_space = -1

        while needle < len(line):
            if needle - start >= true_max_size:
                if last_delimiter != -1:
                    if self.include_wrapped and line[last_delimiter] != '\n':
                        super().add_line(line[start:last_delimiter + 1])
                        needle = last_delimiter + 1
                        start = last_delimiter + 1
                    else:
                        super().add_line(line[start:last_delimiter])
                        needle = last_delimiter + 1
                        start = last_delimiter + 1
                elif last_space != -1:
                    super().add_line(line[start:last_space])
                    needle = last_space + 1
                    start = last_space
                else:
                    super().add_line(line[start:needle])
                    start = needle

                last_delimiter = -1
                last_space = -1

            if line[needle] in self.wrap_on:
                last_delimiter = needle
            elif line[needle] == ' ':
                last_space = needle

            needle += 1

        last_line = line[start:needle]
        if last_line:
            super().add_line(last_line)

        if empty:
            self._current_page.append('')
            self._count += self._linesep_len


class FilePaginator(commands.Paginator):
    """
    A paginator of syntax-highlighted codeblocks, read from a file-like.

    Parameters
    -----------
    fp
        A file-like (implements ``fp.read``) to read the data for this paginator from.
    line_span: Optional[Tuple[int, int]]
        A linespan to read from the file. If None, reads the whole file.
    language_hints: Tuple[str, ...]
        A tuple of strings that may hint to the language of this file.
        This could include filenames, MIME types, or shebangs.
        A shebang present in the actual file will always be prioritized over this.
    """

    def __init__(
        self,
        fp: typing.BinaryIO,
        line_span: typing.Optional[typing.Tuple[int, int]] = None,
        language_hints: typing.Tuple[str, ...] = (),
        **kwargs: typing.Any
    ):
        language = ''

        for hint in language_hints:
            language = get_language(hint)

            if language:
                break

        if not language:
            try:
                language = get_language(fp.name)
            except AttributeError:
                pass

        content, _, file_language = guess_file_traits(fp.read())

        language = file_language or language
        lines = content.split('\n')

        super().__init__(prefix=f'```{language}', suffix='```', **kwargs)

        if line_span:
            if line_span[1] < line_span[0]:
                line_span = (line_span[1], line_span[0])

            if line_span[0] < 1 or line_span[1] > len(lines):
                raise ValueError("Linespan goes out of bounds.")

            lines = lines[line_span[0] - 1:line_span[1]]

        for line in lines:
            self.add_line(line)


class WrappedFilePaginator(FilePaginator, WrappedPaginator):
    """
    Combination of FilePaginator and WrappedPaginator.
    In other words, a FilePaginator that supports line wrapping.
    """


def use_file_check(
    ctx: ContextA,
    size: int
) -> bool:
    """
    A check to determine if uploading a file and relying on Discord's file preview is acceptable over a PaginatorInterface.
    """

    return all([
        size < 50_000,  # Check the text is below the Discord cutoff point;
        not Flags.FORCE_PAGINATOR,  # Check the user hasn't explicitly disabled this;
        (
            # Ensure the user isn't on mobile
            not ctx.author.is_on_mobile()
            if ctx.guild and ctx.bot.intents.presences and isinstance(ctx.author, discord.Member)
            else True
        )
    ])
