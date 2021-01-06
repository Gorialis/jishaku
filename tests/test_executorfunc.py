# -*- coding: utf-8 -*-

"""
jishaku.hljs test
~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import inspect

import pytest

from jishaku.functools import executor_function


def sig(*args, **kwargs):
    """
    Return a signature to make it easier to parameterize this test
    """
    return args, kwargs


@pytest.mark.parametrize(
    ("args", "kwargs", "expected_return"),
    [
        (*sig(1, 2, c=3), (1, 2, 3)),
        (*sig(3, c=4), (3, None, 4)),
        (*sig(a=5, b=6, c=7), (5, 6, 7))
    ]
)
def test_magic_executor(args, kwargs, expected_return):
    loop = asyncio.get_event_loop()

    def non_executor(a, b=None, *, c) -> tuple:
        return a, b, c

    exact_executor = executor_function(non_executor)

    @executor_function
    def redefined_executor(a, b=None, *, c) -> tuple:
        return a, b, c

    assert inspect.signature(non_executor) == inspect.signature(exact_executor)
    assert inspect.signature(non_executor) == inspect.signature(redefined_executor)

    assert non_executor(*args, **kwargs) == expected_return
    assert loop.run_until_complete(exact_executor(*args, **kwargs)) == expected_return
    assert loop.run_until_complete(redefined_executor(*args, **kwargs)) == expected_return
