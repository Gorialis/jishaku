# -*- coding: utf-8 -*-

"""
jishaku.features.filesystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The jishaku filesystem-related commands.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import io
import os
import pathlib
import re

import aiohttp
import discord
from discord.ext import commands

from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.hljs import get_language, guess_file_traits
from jishaku.paginators import PaginatorInterface, WrappedFilePaginator, use_file_check


class FilesystemFeature(Feature):
    """
    Feature containing the filesystem-related commands
    """

    __cat_line_regex = re.compile(r"(?:\.\/+)?(.+?)(?:#L?(\d+)(?:\-L?(\d+))?)?$")

    @Feature.Command(parent="jsk", name="cat")
    async def jsk_cat(self, ctx: commands.Context, argument: str):  # pylint: disable=too-many-locals
        """
        Read out a file, using syntax highlighting if detected.

        Lines and linespans are supported by adding '#L12' or '#L12-14' etc to the end of the filename.
        """

        match = self.__cat_line_regex.search(argument)

        if not match:  # should never happen
            return await ctx.send("Couldn't parse this input.")

        path = match.group(1)

        line_span = None

        if match.group(2):
            start = int(match.group(2))
            line_span = (start, int(match.group(3) or start))

        if not os.path.exists(path) or os.path.isdir(path):
            return await ctx.send(f"`{path}`: No file by that name.")

        size = os.path.getsize(path)

        if size <= 0:
            return await ctx.send(f"`{path}`: Cowardly refusing to read a file with no size stat"
                                  f" (it may be empty, endless or inaccessible).")

        if size > 128 * (1024 ** 2):
            return await ctx.send(f"`{path}`: Cowardly refusing to read a file >128MB.")

        try:
            with open(path, "rb") as file:
                if use_file_check(ctx, size):
                    if line_span:
                        content, *_ = guess_file_traits(file.read())

                        lines = content.split('\n')[line_span[0] - 1:line_span[1]]

                        await ctx.send(file=discord.File(
                            filename=pathlib.Path(file.name).name,
                            fp=io.BytesIO('\n'.join(lines).encode('utf-8'))
                        ))
                    else:
                        await ctx.send(file=discord.File(
                            filename=pathlib.Path(file.name).name,
                            fp=file
                        ))
                else:
                    paginator = WrappedFilePaginator(file, line_span=line_span, max_size=1985)
                    interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                    await interface.send_to(ctx)
        except UnicodeDecodeError:
            return await ctx.send(f"`{path}`: Couldn't determine the encoding of this file.")
        except ValueError as exc:
            return await ctx.send(f"`{path}`: Couldn't read this file, {exc}")

    @Feature.Command(parent="jsk", name="curl")
    async def jsk_curl(self, ctx: commands.Context, url: str):
        """
        Download and display a text file from the internet.

        This command is similar to jsk cat, but accepts a URL.
        """

        # remove embed maskers if present
        url = url.lstrip("<").rstrip(">")

        async with ReplResponseReactor(ctx.message):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.read()
                    hints = (
                        response.content_type,
                        url
                    )
                    code = response.status

            if not data:
                return await ctx.send(f"HTTP response was empty (status code {code}).")

            if use_file_check(ctx, len(data)):  # File "full content" preview limit
                # Shallow language detection
                language = None

                for hint in hints:
                    language = get_language(hint)

                    if language:
                        break

                await ctx.send(file=discord.File(
                    filename=f"response.{language or 'txt'}",
                    fp=io.BytesIO(data)
                ))
            else:
                try:
                    paginator = WrappedFilePaginator(io.BytesIO(data), language_hints=hints, max_size=1985)
                except UnicodeDecodeError:
                    return await ctx.send(f"Couldn't determine the encoding of the response. (status code {code})")
                except ValueError as exc:
                    return await ctx.send(f"Couldn't read response (status code {code}), {exc}")

                interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                await interface.send_to(ctx)
