# -*- coding: utf-8 -*-

"""
jishaku.hljs test
~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect
import typing

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
@pytest.mark.asyncio
async def test_magic_executor(args: typing.Tuple[typing.Any, ...], kwargs: typing.Dict[str, typing.Any], expected_return: typing.Tuple[int, typing.Optional[int], int]):
    def non_executor(a: int, b: typing.Optional[int] = None, *, c: int) -> typing.Tuple[int, typing.Optional[int], int]:
        return a, b, c

    exact_executor = executor_function(non_executor)

    @executor_function
    def redefined_executor(a: int, b: typing.Optional[int] = None, *, c: int) -> typing.Tuple[int, typing.Optional[int], int]:
        return a, b, c

    assert inspect.signature(non_executor) == inspect.signature(exact_executor)
    assert inspect.signature(non_executor) == inspect.signature(redefined_executor)

    assert non_executor(*args, **kwargs) == expected_return
    assert (await exact_executor(*args, **kwargs)) == expected_return
    assert (await redefined_executor(*args, **kwargs)) == expected_return
