# -*- coding: utf-8 -*-

"""
jishaku.repl.disassembly
~~~~~~~~~~~~~~~~~~~~~~~~

Functions pertaining to the disassembly of Python code

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import ast
import dis

import import_expression

from jishaku.repl.scope import Scope

CORO_CODE = f"""
import asyncio

import discord
from discord.ext import commands
from importlib import import_module as {import_expression.constants.IMPORTER}

import jishaku

async def _repl_coroutine({{0}}):
    pass
"""


def wrap_code(code: str, args: str = '') -> ast.Module:
    """
    Wraps code for disassembly.

    This is similar in function to the jishaku.repl.compilation equivalent,
    but due to the different structure required for clean disassemblies,
    it's implemented separately here.
    """

    user_code = import_expression.parse(code, mode='exec')
    mod = import_expression.parse(CORO_CODE.format(args), mode='exec')

    definition = mod.body[-1]  # async def ...:
    assert isinstance(definition, ast.AsyncFunctionDef)

    # Patch user code directly into the function
    definition.body = user_code.body

    ast.fix_missing_locations(mod)

    # We do not use the keyword transformer here, since it might produce misleading disassembly.

    is_asyncgen = any(isinstance(node, ast.Yield) for node in ast.walk(definition))
    last_expr = definition.body[-1]

    # if the last part isn't an expression, ignore it
    if not isinstance(last_expr, ast.Expr):
        return mod

    # if this isn't a generator and the last expression is not a return
    if not is_asyncgen and not isinstance(last_expr.value, ast.Return):
        # copy the value of the expression into a return
        return_stmt = ast.Return(last_expr.value)
        ast.copy_location(return_stmt, last_expr)

        # place the return where the original expression was
        definition.body[-1] = return_stmt

    return mod


def disassemble(code: str, scope: Scope = None, arg_dict: dict = None):
    """
    Disassembles asynchronous code into dis.dis-style bytecode instructions.
    """

    # Similar to AsyncCodeExecutor.__init__
    arg_names = list(arg_dict.keys()) if arg_dict else []

    scope = scope or Scope()

    wrapped = wrap_code(code, args=', '.join(arg_names))
    exec(compile(wrapped, '<repl>', 'exec'), scope.globals, scope.locals)  # pylint: disable=exec-used

    func_def = scope.locals.get('_repl_coroutine') or scope.globals['_repl_coroutine']

    # pylint is gonna really hate this part onwards
    # pylint: disable=protected-access, invalid-name
    co = func_def.__code__

    for instruction in dis._get_instructions_bytes(
        co.co_code, co.co_varnames, co.co_names, co.co_consts,
        co.co_cellvars + co.co_freevars, dict(dis.findlinestarts(co)),
        line_offset=0
    ):
        if instruction.starts_line is not None and instruction.offset > 0:
            yield ''

        yield instruction._disassemble(
            4, False, 4
        )

    # pylint: enable=protected-access, invalid-name
