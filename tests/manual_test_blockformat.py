# -*- coding: utf-8 -*-

"""
jishaku manual blockformat test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This test checks that blockformats look OK and function correctly.
You should run it in a bash-like shell (that supports ANSI codes).

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect

from jishaku.formatting import LineFormatter, MultilineFormatter

if __name__ == '__main__':
    print("== No Annotations Test ==")
    formatter = LineFormatter("one (two three) four")

    print(formatter.output(False, False))
    print(formatter.output(True, False))
    print(formatter.output(True, True))

    print("== Forward Test ==")
    formatter = LineFormatter("one (two three) four")

    formatter.add_annotation("First", (0, 2), 34)
    formatter.add_annotation("Second", (4, 14), 31, 33, 41)
    formatter.add_annotation("Third", (5, 7), 32, 34)
    formatter.add_annotation("Fourth", (9, 13), 33)
    formatter.add_annotation("Fifth", (16, 19), 34)

    print(formatter.output(False, False))
    print(formatter.output(True, False))
    print(formatter.output(True, True))

    print("== Backward Test ==")
    formatter = LineFormatter("one (two three) four")

    formatter.add_annotation("Fifth", (16, 19), 34)
    formatter.add_annotation("Fourth", (9, 13), 33)
    formatter.add_annotation("Third", (5, 7), 32, 34)
    formatter.add_annotation("Second", (4, 14), 31, 33, 41)
    formatter.add_annotation("First", (0, 2), 34)
    formatter.add_annotation("Extra", (9, 13), 35)

    print(formatter.output(False, False))
    print(formatter.output(True, False))
    print(formatter.output(True, True))

    print("== Multiline ==")
    formatter = MultilineFormatter(inspect.cleandoc("""
        one (two three) four
            five six seven eight nine
    """))

    formatter.add_annotation(0, "First", (0, 2), 34)
    formatter.add_annotation(0, "Second", (4, 14), 31, 33, 41)
    formatter.add_annotation(0, "Third", (5, 7), 32, 34)
    formatter.add_annotation(0, "Fourth", (9, 13), 33)
    formatter.add_annotation(0, "Fifth", (16, 19), 34)

    formatter.add_annotation(1, "Second on second line", (9, 11), 31, 33, 41)
    formatter.add_annotation(1, "Whole second line", (4, 23), 35)
    formatter.add_annotation(1, "No span", None, 34)
    # Will not show as a line
    formatter.add_annotation(1, "", (19, 23), None, None, 45)
    formatter.add_annotation(1, "", (20, 20), None, 31, None)
    formatter.add_annotation(1, "Eight with a highlighted i", (19, 23), 33)
    formatter.add_annotation(1, "", (26, 26), None, 36, None)
    formatter.add_annotation(1, "", (25, 28), None, None, 41)
    formatter.add_annotation(1, "Nine with a highlighted i", (25, 28), 32)
    formatter.add_annotation(1, "A small bit after the end", (30, 35), 34)

    print(formatter.output(False, False))
    print(formatter.output(True, False))
    print(formatter.output(True, True))
