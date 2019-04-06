# -*- coding: utf-8 -*-

"""
jishaku.shell test
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import sys

import pytest

from jishaku.shell import ShellReader
from utils import run_async


@run_async
async def test_reader_basic():
    return_data = []

    with ShellReader("echo hi") as reader:
        async for result in reader:
            return_data.append(result)

    assert len(return_data) == 1
    assert return_data[0] == "hi"

    with pytest.raises(asyncio.TimeoutError):
        with ShellReader("sleep 10", timeout=5) as reader:
            async for result in reader:
                pass


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Tests with Linux-only sh syntax"
)
@run_async
async def test_linux():
    return_data = []

    with ShellReader(">&2 echo oops") as reader:
        async for result in reader:
            return_data.append(result)

    assert len(return_data) == 1
    assert return_data[0] == "[stderr] oops"

    return_data = []

    with ShellReader("echo one && echo two") as reader:
        async for result in reader:
            return_data.append(result)

    assert len(return_data) == 2
    assert return_data[0] == "one"
    assert return_data[1] == "two"


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Tests with Windows-only cmd syntax"
)
@run_async
async def test_windows():
    return_data = []

    with ShellReader("cmd /c \"echo one && echo two\"") as reader:
        async for result in reader:
            return_data.append(result)

    assert len(return_data) == 2
    assert return_data[0].strip() == "one"
    assert return_data[1].strip() == "two"
