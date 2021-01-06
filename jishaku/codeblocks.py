# -*- coding: utf-8 -*-

"""
jishaku.codeblocks
~~~~~~~~~~~~~~~~~~

Converters for detecting and obtaining codeblock content

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import collections

__all__ = ('Codeblock', 'codeblock_converter')

Codeblock = collections.namedtuple('Codeblock', 'language content')


def codeblock_converter(argument):
    """
    A converter that strips codeblock markdown if it exists.

    Returns a namedtuple of (language, content).

    :attr:`Codeblock.language` is an empty string if no language was given with this codeblock.
    It is ``None`` if the input was not a complete codeblock.
    """
    if not argument.startswith('`'):
        return Codeblock(None, argument)

    # keep a small buffer of the last chars we've seen
    last = collections.deque(maxlen=3)
    backticks = 0
    in_language = False
    in_code = False
    language = []
    code = []

    for char in argument:
        if char == '`' and not in_code and not in_language:
            backticks += 1  # to help keep track of closing backticks
        if last and last[-1] == '`' and char != '`' or in_code and ''.join(last) != '`' * backticks:
            in_code = True
            code.append(char)
        if char == '\n':  # \n delimits language and code
            in_language = False
            in_code = True
        # we're not seeing a newline yet but we also passed the opening ```
        elif ''.join(last) == '`' * 3 and char != '`':
            in_language = True
            language.append(char)
        elif in_language:  # we're in the language after the first non-backtick character
            if char != '\n':
                language.append(char)

        last.append(char)

    if not code and not language:
        code[:] = last

    return Codeblock(''.join(language), ''.join(code[len(language):-backticks]))
