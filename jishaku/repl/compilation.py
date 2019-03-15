# -*- coding: utf-8 -*-

"""
jishaku.repl.compilation
~~~~~~~~~~~~~~~~~~~~~~~~

Constants, functions and classes related to classifying, compiling and executing Python code.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import ast
import asyncio
import inspect
import sys
import textwrap

import import_expression

from .scope import Scope

CORO_CODE = """
async def _repl_coroutine({{0}}):
    import asyncio
    from importlib import import_module as {0}

    import aiohttp
    import discord
    from discord.ext import commands

    try:
        import jishaku
    except ImportError:
        jishaku = None  # keep working even if in panic recovery mode

    try:
        pass
{{1}}
    finally:
        if hasattr(jishaku, 'repl'):
            _async_executor = jishaku.repl.get_parent_var('async_executor', skip_frames=1)
            if _async_executor:
                _async_executor.scope.globals.update(locals())
""".format(import_expression.constants.IMPORTER)


def wrap_code(code: str, args: str = '') -> ast.Module:
    """
    Compiles Python code into an async function or generator,
    and automatically adds return if the function body is a single evaluation.
    Also adds inline import expression support.
    """

    if sys.version_info >= (3, 7):
        user_code = import_expression.parse(code, mode='exec')
        injected = ''
    else:
        injected = code

    mod = import_expression.parse(CORO_CODE.format(args, textwrap.indent(injected, ' ' * 8)), mode='exec')

    definition = mod.body[-1]  # async def ...:
    assert isinstance(definition, ast.AsyncFunctionDef)

    try_block = definition.body[-1]  # try:
    assert isinstance(try_block, ast.Try)

    if sys.version_info >= (3, 7):
        try_block.body.extend(user_code.body)
    else:
        ast.increment_lineno(mod, -16)  # bring line numbers back in sync with repl

    ast.fix_missing_locations(mod)

    is_asyncgen = any(isinstance(node, ast.Yield) for node in ast.walk(try_block))

    last_expr = try_block.body[-1]

    # if the last part isn't an expression, ignore it
    if not isinstance(last_expr, ast.Expr):
        return mod

    # if the last expression is not a yield
    if not isinstance(last_expr.value, ast.Yield):
        # copy the expression into a return/yield
        if is_asyncgen:
            # copy the value of the expression into a yield
            yield_stmt = ast.Yield(last_expr.value)
            ast.copy_location(yield_stmt, last_expr)
            # place the yield into its own expression
            yield_expr = ast.Expr(yield_stmt)
            ast.copy_location(yield_expr, last_expr)

            # place the yield where the original expression was
            try_block.body[-1] = yield_expr
        else:
            # copy the expression into a return
            return_stmt = ast.Return(last_expr.value)
            ast.copy_location(return_stmt, last_expr)

            # place the return where the original expression was
            try_block.body[-1] = return_stmt

    return mod


class AsyncCodeExecutor:  # pylint: disable=too-few-public-methods
    """
    Executes/evaluates Python code inside of an async function or generator.

    Example
    -------

    .. code:: python3

        total = 0

        # prints 1, 2 and 3
        async for x in AsyncCodeExecutor('yield 1; yield 2; yield 3'):
            total += x
            print(x)

        # prints 6
        print(total)
    """

    __slots__ = ('args', 'arg_names', 'code', 'loop', 'scope')

    def __init__(self, code: str, scope: Scope = None, arg_dict: dict = None, loop: asyncio.BaseEventLoop = None):
        self.args = []
        self.arg_names = []

        if arg_dict:
            for key, value in arg_dict.items():
                self.arg_names.append(key)
                self.args.append(value)

        self.code = wrap_code(code, args=', '.join(self.arg_names))
        self.scope = scope or Scope()
        self.loop = loop or asyncio.get_event_loop()

    def __aiter__(self):
        exec(compile(self.code, '<repl>', 'exec'), self.scope.globals, self.scope.locals)  # pylint: disable=exec-used
        func_def = self.scope.locals.get('_repl_coroutine') or self.scope.globals['_repl_coroutine']

        return self.traverse(func_def)

    async def traverse(self, func):
        """
        Traverses an async function or generator, yielding each result.

        This function is private. The class should be used as an iterator instead of using this method.
        """

        # this allows the reference to be stolen
        async_executor = self

        if inspect.isasyncgenfunction(func):
            async for result in func(*async_executor.args):
                yield result
        else:
            yield await func(*async_executor.args)
