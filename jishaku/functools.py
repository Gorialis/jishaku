# -*- coding: utf-8 -*-

"""
jishaku.functools
~~~~~~~~~~~~~~~~~

Function-related tools for Jishaku.

:copyright: (c) 2020 Devon (Gorialis) R
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


class AsyncSender:
    """
    Storage and control flow class that allows prettier value sending to async iterators.

    Example
    --------

    .. code:: python3

        async def foo():
            print("foo yielding 1")
            x = yield 1
            print(f"foo received {x}")
            yield 3

        async for send, result in AsyncSender(foo()):
            print(f"asyncsender received {result}")
            send(2)

    Produces:

    .. code::

        foo yielding 1
        asyncsender received 1
        foo received 2
        asyncsender received 3
    """

    __slots__ = ('iterator', 'send_value')

    def __init__(self, iterator):
        self.iterator = iterator
        self.send_value = None

    def __aiter__(self):
        return self._internal(self.iterator.__aiter__())

    async def _internal(self, base):
        try:
            while True:
                # Send the last value to the iterator
                value = await base.asend(self.send_value)
                # Reset it incase one is not sent next iteration
                self.send_value = None
                # Yield sender and iterator value
                yield self.set_send_value, value
        except StopAsyncIteration:
            pass

    def set_send_value(self, value):
        """
        Sets the next value to be sent to the iterator.

        This is provided by iteration of this class and should
        not be called directly.
        """

        self.send_value = value
