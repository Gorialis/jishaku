# -*- coding: utf-8 -*-

"""
jishaku ast tree generation test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2022 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect

from jishaku.repl.disassembly import create_tree


def test_ast_missing_fields():
    # should not raise
    create_tree(inspect.cleandoc("""
        def h(*, a):
            print(a)
    """), use_ansi=False)
