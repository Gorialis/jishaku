# -*- coding: utf-8 -*-

"""
jishaku test utils
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import contextlib
import functools
from unittest import mock


def run_async(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))

    return inner


def magic_coro_mock():
    coro = mock.MagicMock(name="coro_result")
    coro_func = mock.MagicMock(name="coro_function", side_effect=asyncio.coroutine(coro))
    coro_func.coro = coro

    return coro_func


def mock_coro(*args, **kwargs):
    return mock.patch.object(*args, new_callable=magic_coro_mock, **kwargs)


@contextlib.contextmanager
def mock_ctx():
    ctx = mock.MagicMock()

    with mock_coro(ctx, 'send'):
        yield ctx
