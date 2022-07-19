# -*- coding: utf-8 -*-

"""
jishaku.repl.compilation
~~~~~~~~~~~~~~~~~~~~~~~~

Constants, functions and classes related to classifying, compiling and executing Python code.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import ast
import asyncio
import inspect
import linecache
import typing

import import_expression  # type: ignore

from jishaku.functools import AsyncSender
from jishaku.repl.scope import Scope
from jishaku.repl.walkers import KeywordTransformer

CORO_CODE = f"""
async def _repl_coroutine({{0}}):
    import asyncio
    from importlib import import_module as {import_expression.constants.IMPORTER}

    import aiohttp
    import discord
    from discord.ext import commands

    try:
        import jishaku
    except ImportError:
        jishaku = None  # keep working even if in panic recovery mode

    try:
        pass
    finally:
        _async_executor.scope.globals.update(locals())
"""


def wrap_code(code: str, args: str = '', auto_return: bool = True) -> ast.Module:
    """
    Compiles Python code into an async function or generator,
    and automatically adds return if the function body is a single evaluation.
    Also adds inline import expression support.
    """

    user_code: ast.Module = import_expression.parse(code, mode='exec')  # type: ignore
    mod: ast.Module = import_expression.parse(CORO_CODE.format(args), mode='exec')  # type: ignore

    for node in ast.walk(mod):
        node.lineno = -100_000
        node.end_lineno = -100_000

    definition = mod.body[-1]  # async def ...:
    assert isinstance(definition, ast.AsyncFunctionDef)

    try_block = definition.body[-1]  # try:
    assert isinstance(try_block, ast.Try)

    try_block.body.extend(user_code.body)

    ast.fix_missing_locations(mod)

    KeywordTransformer().generic_visit(try_block)

    # if auto return is disabled, we're done here
    if not auto_return:
        return mod

    last_expr = try_block.body[-1]

    # if the last part isn't an expression, ignore it
    if not isinstance(last_expr, ast.Expr):
        return mod

    # if the last expression is not a yield
    if not isinstance(last_expr.value, ast.Yield):
        # copy the value of the expression into a yield
        yield_stmt = ast.Yield(last_expr.value)
        ast.copy_location(yield_stmt, last_expr)
        # place the yield into its own expression
        yield_expr = ast.Expr(yield_stmt)
        ast.copy_location(yield_expr, last_expr)

        # place the yield where the original expression was
        try_block.body[-1] = yield_expr

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

    __slots__ = ('args', 'arg_names', 'code', 'loop', 'scope', 'source', '_function')

    def __init__(
        self,
        code: str,
        scope: typing.Optional[Scope] = None,
        arg_dict: typing.Optional[typing.Dict[str, typing.Any]] = None,
        convertables: typing.Optional[typing.Dict[str, str]] = None,
        loop: typing.Optional[asyncio.BaseEventLoop] = None,
        auto_return: bool = True,
    ):
        self.args = [self]
        self.arg_names = ['_async_executor']

        if arg_dict:
            for key, value in arg_dict.items():
                self.arg_names.append(key)
                self.args.append(value)

        self.source = code

        try:
            self.code = wrap_code(code, args=', '.join(self.arg_names), auto_return=auto_return)
        except (SyntaxError, IndentationError) as first_error:
            if not convertables:
                raise

            try:
                for key, value in convertables.items():
                    code = code.replace(key, value)
                self.code = wrap_code(code, args=', '.join(self.arg_names))
            except (SyntaxError, IndentationError) as second_error:
                raise second_error from first_error

        self.scope = scope or Scope()
        self.loop = loop or asyncio.get_event_loop()
        self._function = None

    @property
    def function(self) -> typing.Callable[..., typing.Union[
        typing.Awaitable[typing.Any],
        typing.AsyncGenerator[typing.Any, typing.Any]
    ]]:
        """
        The function object produced from compiling the code.
        If the code has not been compiled yet, it will be done upon first access.
        """

        if self._function is not None:
            return self._function

        exec(compile(self.code, '<repl>', 'exec'), self.scope.globals, self.scope.locals)  # pylint: disable=exec-used
        self._function = self.scope.locals.get('_repl_coroutine') or self.scope.globals['_repl_coroutine']

        return self._function

    def create_linecache(self) -> typing.List[str]:
        """
        Populates the line cache with the current source.
        Can be performed before printing a traceback to show correct source lines.
        """

        lines = [line + '\n' for line in self.source.splitlines()]

        linecache.cache['<repl>'] = (
            len(self.source),  # Source length
            None,  # Time modified (None bypasses expunge)
            lines,  # Line list
            '<repl>'  # 'True' filename
        )

        return lines

    def __aiter__(self) -> typing.AsyncGenerator[typing.Any, typing.Any]:
        return self.traverse(self.function)

    async def traverse(
        self,
        func: typing.Callable[..., typing.Union[
            typing.Awaitable[typing.Any],
            typing.AsyncGenerator[typing.Any, typing.Any]
        ]]
    ) -> typing.AsyncGenerator[typing.Any, typing.Any]:
        """
        Traverses an async function or generator, yielding each result.

        This function is private. The class should be used as an iterator instead of using this method.
        """

        try:
            if inspect.isasyncgenfunction(func):
                func_g: typing.Callable[..., typing.AsyncGenerator[typing.Any, typing.Any]] = func  # type: ignore
                async for send, result in AsyncSender(func_g(*self.args)):  # type: ignore
                    send((yield result))
            else:
                func_a: typing.Callable[..., typing.Awaitable[typing.Any]] = func  # type: ignore
                yield await func_a(*self.args)
        except Exception:  # pylint: disable=broad-except
            # Falsely populate the linecache to make the REPL line appear in tracebacks
            self.create_linecache()

            raise
