# -*- coding: utf-8 -*-

"""
jishaku manual specialist test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This test checks that blockformats look OK and function correctly.
You should run it in a bash-like shell (that supports ANSI codes).

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio

from jishaku.formatting import MultilineFormatter
from jishaku.repl import AsyncCodeExecutor
from jishaku.repl.disassembly import get_adaptive_spans

CODE = '''
import math

def f_to_c(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    x = f - 32
    return x * 5 / 9

def c_to_f(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    x = c * 9 / 5
    return x + 32

TEST_VALUES = [-459.67, -273.15, 0.0, 32.0, 42.0, 273.15, 100.0, 212.0, 373.15]

def test_conversions() -> None:
    for t in TEST_VALUES:
        assert_round_trip(t)

def assert_round_trip(t: float) -> None:
    # Round-trip Fahrenheit through Celsius:
    assert math.isclose(t, f_to_c(c_to_f(t))), f"{t} F -> C -> F failed!"
    # Round-trip Celsius through Fahrenheit:
    assert math.isclose(t, c_to_f(f_to_c(t))), f"{t} C -> F -> C failed!"

yield test_conversions()

'''


async def manual_t():
    """
    Manual test to see if specialist annotations work
    """

    executor = AsyncCodeExecutor(CODE)
    formatter = MultilineFormatter(CODE)

    async for result in executor:
        print(result)

    for (index, (instruction, line, span, specialized, adaptive)) in enumerate(get_adaptive_spans(executor.function.__code__)):
        print(instruction.opname, line)

        if line - 1 < len(formatter.lines):
            formatter.add_annotation(line - 1, instruction.opname, span, (index % 6) + 31, None, 42 if specialized else 41 if adaptive else None)

    print(formatter.output(True, True))


if __name__ == '__main__':
    asyncio.run(manual_t())
