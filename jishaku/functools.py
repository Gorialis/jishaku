# -*- coding: utf-8 -*-

"""
jishaku.functools
~~~~~~~~~~~~~~~~~

Function-related tools for Jishaku.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import functools
import typing


def executor_function(sync_function: typing.Callable):
    """A decorator that wraps a sync function in an executor, changing it into an async function.

    This allows processing functions to be wrapped and used immediately as an async function.

    Examples
    ---------

    Pushing processing with the Python Imaging Library into an executor:

    .. code-block:: python3

        from io import BytesIO
        from PIL import Image

        from jishaku.functools import executor_function


        @executor_function
        def color_processing(color: discord.Color):
            with Image.new('RGB', (64, 64), color.to_rgb()) as im:
                buff = BytesIO()
                im.save(buff, 'png')

            buff.seek(0)
            return buff

        @bot.command()
        async def color(ctx: commands.Context, color: discord.Color=None):
            color = color or ctx.author.color
            buff = await color_processing(color=color)

            await ctx.send(file=discord.File(fp=buff, filename='color.png'))
    """

    @functools.wraps(sync_function)
    async def sync_wrapper(*args, **kwargs):
        """
        Asynchronous function that wraps a sync function with an executor.
        """

        loop = asyncio.get_event_loop()
        internal_function = functools.partial(sync_function, *args, **kwargs)
        return await loop.run_in_executor(None, internal_function)

    return sync_wrapper
