# -*- coding: utf-8 -*-

"""
jishaku converter test
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect

from jishaku.codeblocks import Codeblock, codeblock_converter


def test_codeblock_converter():
    text = """
    ```py
    one
    ```
    """

    codeblock = codeblock_converter(inspect.cleandoc(text))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'one'
    assert codeblock.language == 'py'

    text = """
    ```sql
    two
    ```
    """

    codeblock = codeblock_converter(inspect.cleandoc(text))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'two'
    assert codeblock.language == 'sql'

    text = """
    ```txt
    three
    ```
    """

    codeblock = codeblock_converter(inspect.cleandoc(text))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'three'
    assert codeblock.language == 'txt'

    text = """
    ```
    four
    ```
    """

    codeblock = codeblock_converter(inspect.cleandoc(text))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'four'
    assert not codeblock.language

    text = "five"

    codeblock = codeblock_converter(inspect.cleandoc(text))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'five'
    assert not codeblock.language

    text = """
    six
    ```
    """

    codeblock = codeblock_converter(inspect.cleandoc(text))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'six\n```'
    assert not codeblock.language

    text = ""

    codeblock = codeblock_converter(inspect.cleandoc(text))

    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == ''
    assert not codeblock.language

    text = """
    ```
    se``ven
    ```
    """

    codeblock = codeblock_converter(inspect.cleandoc(text))
    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'se``ven'
    assert not codeblock.language

    text = "``ei`ght``"
    codeblock = codeblock_converter(text)
    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'ei`ght'
    assert not codeblock.language

    text = "`nine`"
    codeblock = codeblock_converter(text)
    assert isinstance(codeblock, Codeblock)
    assert codeblock.content.strip() == 'nine'
    assert not codeblock.language
