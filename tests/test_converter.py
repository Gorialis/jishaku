# -*- coding: utf-8 -*-

"""
jishaku converter test
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import inspect
import unittest

from jishaku.codeblocks import Codeblock, CodeblockConverter


class ConverterTest(unittest.TestCase):
    def test_codeblock_converter(self):
        loop = asyncio.get_event_loop()

        conv = CodeblockConverter()

        text = """
        ```py
        one
        ```
        """

        codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

        self.assertIsInstance(codeblock, Codeblock)
        self.assertEqual(codeblock.content.strip(), 'one')
        self.assertEqual(codeblock.language, 'py')

        text = """
        ```sql
        two
        ```
        """

        codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

        self.assertIsInstance(codeblock, Codeblock)
        self.assertEqual(codeblock.content.strip(), 'two')
        self.assertEqual(codeblock.language, 'sql')

        text = """
        ```txt
        three
        ```
        """

        codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

        self.assertIsInstance(codeblock, Codeblock)
        self.assertEqual(codeblock.content.strip(), 'three')
        self.assertEqual(codeblock.language, 'txt')

        text = """
        ```
        four
        ```
        """

        codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

        self.assertIsInstance(codeblock, Codeblock)
        self.assertEqual(codeblock.content.strip(), 'four')
        self.assertEqual(codeblock.language, '')
        self.assertFalse(codeblock.language)

        text = "five"

        codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

        self.assertIsInstance(codeblock, Codeblock)
        self.assertEqual(codeblock.content.strip(), 'five')
        self.assertEqual(codeblock.language, None)
        self.assertFalse(codeblock.language)

        text = """
        six
        ```
        """

        codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

        self.assertIsInstance(codeblock, Codeblock)
        self.assertEqual(codeblock.content.strip(), 'six')
        self.assertEqual(codeblock.language, None)
        self.assertFalse(codeblock.language)

        text = ""

        codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

        self.assertIsInstance(codeblock, Codeblock)
        self.assertEqual(codeblock.content.strip(), '')
        self.assertEqual(codeblock.language, None)
        self.assertFalse(codeblock.language)
