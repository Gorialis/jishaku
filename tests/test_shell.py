# -*- coding: utf-8 -*-

"""
jishaku.shell test
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2018 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import unittest

from jishaku.shell import ShellReader


class ShellTest(unittest.TestCase):

    def test_executor(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.internal())

    async def internal(self):
        return_data_1 = []

        with ShellReader("echo hi") as reader:
            async for result in reader:
                return_data_1.append(result)

        self.assertEqual(len(return_data_1), 1)
        self.assertEqual(return_data_1[0], "hi")

        return_data_2 = []

        with ShellReader(">&2 echo oops") as reader:
            async for result in reader:
                return_data_2.append(result)

        self.assertEqual(len(return_data_2), 1)
        self.assertEqual(return_data_2[0], "[stderr] oops")

        return_data_3 = []

        with ShellReader("echo one; echo two") as reader:
            async for result in reader:
                return_data_3.append(result)

        self.assertEqual(len(return_data_3), 2)
        self.assertEqual(return_data_3[0], "one")
        self.assertEqual(return_data_3[1], "two")

        hit_exception = False

        try:
            with ShellReader("echo one; sleep 10; echo two", timeout=5) as reader:
                async for result in reader:
                    pass
        except asyncio.TimeoutError:
            hit_exception = True

        self.assertTrue(hit_exception)
