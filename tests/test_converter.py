# -*- coding: utf-8 -*-

"""
jishaku converter test
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import inspect

from jishaku.codeblocks import Codeblock, CodeblockConverter


def test_codeblock_converter():
    loop = asyncio.get_event_loop()

    conv = CodeblockConverter()

    text = """
    ```py
    one
    ```
    """

    codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'one'
    assert codeblock.language == 'py'

    text = """
    ```sql
    two
    ```
    """

    codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'two'
    assert codeblock.language == 'sql'

    text = """
    ```txt
    three
    ```
    """

    codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'three'
    assert codeblock.language == 'txt'

    text = """
    ```
    four
    ```
    """

    codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'four'
    assert codeblock.language == ''
    assert not codeblock.language

    text = "five"

    codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'five'
    assert codeblock.language is None
    assert not codeblock.language

    text = """
    six
    ```
    """

    codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'six'
    assert codeblock.language is None
    assert not codeblock.language

    text = ""

    codeblock = loop.run_until_complete(conv.convert(None, inspect.cleandoc(text)))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == ''
    assert codeblock.language is None
    assert not codeblock.language
