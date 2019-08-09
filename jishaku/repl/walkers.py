# -*- coding: utf-8 -*-

"""
jishaku.repl.walkers
~~~~~~~~~~~~~~~~~~~~

AST walkers for code transformation and analysis.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import ast

# pylint: disable=no-self-use,invalid-name,missing-docstring


class KeywordTransformer(ast.NodeTransformer):
    """
    This transformer:
    - Converts return-with-value into yield & return
    - Converts bare deletes into conditional global pops
    """

    def visit_FunctionDef(self, node):
        # Do not affect nested function definitions
        return node

    def visit_AsyncFunctionDef(self, node):
        # Do not affect nested async function definitions
        return node

    def visit_ClassDef(self, node):
        # Do not affect nested class definitions
        return node

    def visit_Return(self, node):
        # Do not modify valueless returns
        if node.value is None:
            return node

        # Otherwise, replace the return with a yield & valueless return
        return ast.If(
            test=ast.NameConstant(
                value=True,  # if True; aka unconditional, will be optimized out
                lineno=node.lineno,
                col_offset=node.col_offset
            ),
            body=[
                # yield the value to be returned
                ast.Expr(
                    value=ast.Yield(
                        value=node.value,
                        lineno=node.lineno,
                        col_offset=node.col_offset
                    ),
                    lineno=node.lineno,
                    col_offset=node.col_offset
                ),
                # return valuelessly
                ast.Return(
                    value=None,
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
            ],
            orelse=[],
            lineno=node.lineno,
            col_offset=node.col_offset
        )

    def visit_Delete(self, node):
        """
        This converter replaces bare deletes with conditional global pops.

        It is roughly equivalent to transforming:

        .. code:: python

            del foobar

        into:

        .. code:: python

            if 'foobar' in globals():
                globals().pop('foobar')
            else:
                del foobar

        This thus makes deletions in retain mode work more-or-less as intended.
        """

        body = []
        for target in node.targets:  # for each target to be deleted, e.g. `del {x}, {y.z}, {z[1]}`
            if not isinstance(target, ast.Name):
                # if it's a subscript or attribute access, pass it through unmodified
                body.append(
                    ast.Delete(
                        targets=[target],
                        lineno=node.lineno,
                        col_offset=node.col_offset
                    )
                )
                continue

            body.append(
                ast.If(
                    # if 'x' in globals():
                    test=ast.Compare(
                        # 'x'
                        left=ast.Str(
                            s=target.id,
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        ),
                        ops=[
                            # in
                            ast.In(
                                lineno=node.lineno,
                                col_offset=node.col_offset
                            )
                        ],
                        comparators=[
                            # globals()
                            self.globals_call(node)
                        ],
                        lineno=node.lineno,
                        col_offset=node.col_offset
                    ),
                    body=[
                        ast.Expr(
                            # globals().pop('x')
                            value=ast.Call(
                                # globals().pop
                                func=ast.Attribute(
                                    value=self.globals_call(node),
                                    attr='pop',
                                    ctx=ast.Load(),
                                    lineno=node.lineno,
                                    col_offset=node.col_offset
                                ),
                                args=[
                                    # 'x'
                                    ast.Str(
                                        s=target.id,
                                        lineno=node.lineno,
                                        col_offset=node.col_offset
                                    )
                                ],
                                keywords=[],
                                lineno=node.lineno,
                                col_offset=node.col_offset
                            ),
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        )
                    ],
                    # else:
                    orelse=[
                        # del x
                        ast.Delete(
                            targets=[target],
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        )
                    ],
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
            )

        return ast.If(
            test=ast.NameConstant(
                value=True,  # if True; aka unconditional, will be optimized out
                lineno=node.lineno,
                col_offset=node.col_offset
            ),
            body=body,
            orelse=[],
            lineno=node.lineno,
            col_offset=node.col_offset
        )

    def globals_call(self, node):
        """
        Creates an AST node that calls globals().
        """

        return ast.Call(
            func=ast.Name(
                id='globals',
                ctx=ast.Load(),
                lineno=node.lineno,
                col_offset=node.col_offset
            ),
            args=[],
            keywords=[],
            lineno=node.lineno,
            col_offset=node.col_offset
        )
