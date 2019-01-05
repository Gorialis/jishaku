# -*- coding: utf-8 -*-

"""
jishaku.hljs test
~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import inspect
import unittest

from jishaku.functools import executor_function


class ExecutorFunctionTest(unittest.TestCase):
    def test_magic_executor(self):
        loop = asyncio.get_event_loop()

        def non_executor(a, b=None, *, c) -> tuple:
            return a, b, c

        @executor_function
        def magic_executor(a, b=None, *, c) -> tuple:
            return a, b, c

        self.assertEqual(loop.run_until_complete(magic_executor(1, 2, c=3)), (1, 2, 3))
        self.assertEqual(loop.run_until_complete(magic_executor(3, c=4)), (3, None, 4))
        self.assertEqual(loop.run_until_complete(magic_executor(a=5, b=6, c=7)), (5, 6, 7))

        self.assertEqual(loop.run_until_complete(magic_executor(1, 2, c=3)), non_executor(1, 2, c=3))
        self.assertEqual(loop.run_until_complete(magic_executor(3, c=4)), non_executor(3, c=4))
        self.assertEqual(loop.run_until_complete(magic_executor(a=5, b=6, c=7)), non_executor(a=5, b=6, c=7))

        self.assertEqual(inspect.signature(non_executor), inspect.signature(magic_executor))
