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
import re

import aiohttp
from discord.ext import commands

from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.paginators import PaginatorInterface, WrappedFilePaginator


class FilesystemFeature(Feature):
    """
    Feature containing the filesystem-related commands
    """

    __cat_line_regex = re.compile(r"(?:\.\/+)?(.+?)(?:#L?(\d+)(?:\-L?(\d+))?)?$")

    @Feature.Command(parent="jsk", name="cat")
    async def jsk_cat(self, ctx: commands.Context, argument: str):
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

        if size > 50 * (1024 ** 2):
            return await ctx.send(f"`{path}`: Cowardly refusing to read a file >50MB.")

        try:
            with open(path, "rb") as file:
                paginator = WrappedFilePaginator(file, line_span=line_span, max_size=1985)
        except UnicodeDecodeError:
            return await ctx.send(f"`{path}`: Couldn't determine the encoding of this file.")
        except ValueError as exc:
            return await ctx.send(f"`{path}`: Couldn't read this file, {exc}")

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        await interface.send_to(ctx)

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

            try:
                paginator = WrappedFilePaginator(io.BytesIO(data), language_hints=hints, max_size=1985)
            except UnicodeDecodeError:
                return await ctx.send(f"Couldn't determine the encoding of the response. (status code {code})")
            except ValueError as exc:
                return await ctx.send(f"Couldn't read response (status code {code}), {exc}")

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            await interface.send_to(ctx)
