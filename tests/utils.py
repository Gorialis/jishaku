# -*- coding: utf-8 -*-

"""
jishaku test utils
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import contextlib
import functools
import random
from unittest import mock
from unittest.mock import patch

from discord.ext import commands


def run_async(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))

    return inner


def sentinel():
    return random.randint(10**16, 10**18)


def magic_coro_mock():
    coro = mock.MagicMock(name="coro_result")
    coro_func = mock.MagicMock(name="coro_function", side_effect=asyncio.coroutine(coro))
    coro_func.coro = coro

    return coro_func


def mock_coro(*args, **kwargs):
    return patch.object(*args, new_callable=magic_coro_mock, **kwargs)


@contextlib.contextmanager
def nested_mocks(ctx, standards, coros):
    with contextlib.ExitStack() as stack:
        for attribute_set in standards:
            attributes = attribute_set[:-1]
            mock_target = attribute_set[-1]

            target = ctx
            for attribute in attributes:
                target = getattr(target, attribute)

            stack.enter_context(patch.object(target, mock_target))

        for attribute_set in coros:
            attributes = attribute_set[:-1]
            mock_target = attribute_set[-1]

            target = ctx
            for attribute in attributes:
                target = getattr(target, attribute)

            stack.enter_context(mock_coro(target, mock_target))

        yield


@contextlib.contextmanager
def mock_ctx(bot: commands.Bot = None):
    ctx = mock.MagicMock(name='ctx')

    standard_mocks = []

    coro_mocks = [
        ('bot', 'get_context'),
        ('message', 'channel', 'send'),
        ('message', 'channel', 'send', 'coro', 'return_value', 'add_reaction'),
        ('message', 'channel', 'send', 'coro', 'return_value', 'delete'),
        ('message', 'channel', 'send', 'coro', 'return_value', 'edit'),
        ('message', 'channel', 'send', 'coro', 'return_value', 'remove_reaction'),
        ('reinvoke',)
    ]

    if bot:
        ctx.bot = bot
        standard_mocks.append(
            ('bot', '_connection', 'user')
        )
    else:
        ctx.bot.loop = asyncio.get_event_loop()
        standard_mocks.append(
            ('bot', 'user')
        )

    with nested_mocks(ctx, standard_mocks, coro_mocks):
        ctx.author = ctx.message.author
        ctx.channel = ctx.message.channel
        ctx.guild = ctx.message.guild
        ctx.send = ctx.message.channel.send

        yield ctx
