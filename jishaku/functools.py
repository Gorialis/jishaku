# -*- coding: utf-8 -*-

"""
jishaku.functools
~~~~~~~~~~~~~~~~~

Function-related tools for Jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import functools
import sys
import typing

T = typing.TypeVar('T')

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
    P = ParamSpec('P')
else:
    P = typing.ParamSpec('P')  # pylint: disable=no-member


def executor_function(sync_function: typing.Callable[P, T]) -> typing.Callable[P, typing.Awaitable[T]]:
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
    async def sync_wrapper(*args: P.args, **kwargs: P.kwargs):
        """
        Asynchronous function that wraps a sync function with an executor.
        """

        loop = asyncio.get_event_loop()
        internal_function = functools.partial(sync_function, *args, **kwargs)
        return await loop.run_in_executor(None, internal_function)

    return sync_wrapper


U = typing.TypeVar('U')


class AsyncSender(typing.Generic[T, U]):
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

    def __init__(self, iterator: typing.AsyncGenerator[T, typing.Optional[U]]):
        self.iterator = iterator
        self.send_value: U = None

    def __aiter__(self) -> typing.AsyncGenerator[typing.Tuple[typing.Callable[[typing.Optional[U]], None], T], None]:
        return self._internal(self.iterator.__aiter__())  # type: ignore

    async def _internal(
        self,
        base: typing.AsyncGenerator[T, typing.Optional[U]]
    ) -> typing.AsyncGenerator[typing.Tuple[typing.Callable[[typing.Optional[U]], None], T], None]:
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

    def set_send_value(self, value: typing.Optional[U]):
        """
        Sets the next value to be sent to the iterator.

        This is provided by iteration of this class and should
        not be called directly.
        """

        self.send_value = value
