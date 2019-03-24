# -*- coding: utf-8 -*-

"""
jishaku.shell test
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import sys
import unittest

from jishaku.shell import ShellReader

WINDOWS = sys.platform == "win32"


class ShellTest(unittest.TestCase):

    def test_executor(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.internal())

    async def internal(self):
        return_data = []

        with ShellReader("echo hi") as reader:
            async for result in reader:
                return_data.append(result)

        self.assertEqual(len(return_data), 1)
        self.assertEqual(return_data[0], "hi")

        # Linux-only tests
        if not WINDOWS:
            return_data = []

            with ShellReader(">&2 echo oops") as reader:
                async for result in reader:
                    return_data.append(result)

            self.assertEqual(len(return_data), 1)
            self.assertEqual(return_data[0], "[stderr] oops")

            return_data = []

            with ShellReader("echo one && echo two") as reader:
                async for result in reader:
                    return_data.append(result)

            self.assertEqual(len(return_data), 2)
            self.assertEqual(return_data[0], "one")
            self.assertEqual(return_data[1], "two")

        # Windows-only tests
        if WINDOWS:
            return_data = []

            with ShellReader("cmd /c \"echo one && echo two\"") as reader:
                async for result in reader:
                    return_data.append(result)

            self.assertEqual(len(return_data), 2)
            self.assertEqual(return_data[0].strip(), "one")
            self.assertEqual(return_data[1].strip(), "two")

        hit_exception = False

        try:
            with ShellReader("sleep 10", timeout=5) as reader:
                async for result in reader:
                    pass
        except asyncio.TimeoutError:
            hit_exception = True

        self.assertTrue(hit_exception)
