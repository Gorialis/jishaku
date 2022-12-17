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
import typing

import import_expression  # type: ignore

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

    user_code: ast.Module = import_expression.parse(code, mode='exec')  # type: ignore
    mod: ast.Module = import_expression.parse(CORO_CODE.format(args), mode='exec')  # type: ignore

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


def disassemble(
    code: str,
    scope: typing.Optional[Scope] = None,
    arg_dict: typing.Optional[typing.Dict[str, typing.Any]] = None
) -> typing.Generator[str, None, None]:
    """
    Disassembles asynchronous code into dis.dis-style bytecode instructions.
    """

    # Similar to AsyncCodeExecutor.__init__
    arg_names = list(arg_dict.keys()) if arg_dict else []

    scope = scope or Scope()

    wrapped = wrap_code(code, args=', '.join(arg_names))
    exec(compile(wrapped, '<repl>', 'exec'), scope.globals, scope.locals)  # pylint: disable=exec-used

    func_def = scope.locals.get('_repl_coroutine') or scope.globals['_repl_coroutine']

    for instruction in dis.get_instructions(  # type: ignore
        func_def, first_line=0
    ):
        instruction: dis.Instruction

        if instruction.starts_line is not None and instruction.offset > 0:
            yield ''

        # pylint: disable=protected-access
        yield instruction._disassemble(  # type: ignore
            4, False, 4
        )
        # pylint: enable=protected-access


TREE_CONTINUE = ('\N{BOX DRAWINGS HEAVY VERTICAL AND RIGHT}', '\N{BOX DRAWINGS HEAVY VERTICAL}')
TREE_LAST = ('\N{BOX DRAWINGS HEAVY UP AND RIGHT}', '\N{BOX DRAWINGS LIGHT QUADRUPLE DASH VERTICAL}')


def maybe_ansi(text: str, level: int, use_ansi: bool = True) -> str:
    """
    Adds an ANSI highlight corresponding to the level, if enabled
    """

    return f"\u001b[{(level % 6) + 31}m{text}\u001b[0m" if use_ansi else text


def format_ast_block(
    node: typing.Union[typing.List[ast.AST], ast.AST],
    header: str = '',
    level: int = 0,
    through: bool = False,
    use_ansi: bool = True
) -> typing.Generator[str, None, None]:
    """
    Formats either an AST node, a list of AST nodes, or a constant.
    """

    if isinstance(node, ast.AST):
        node = [node]
        header += ": "
    elif not isinstance(node, list):  # type: ignore
        branch, _ = TREE_CONTINUE if through else TREE_LAST
        branch = maybe_ansi(f"{branch} {header}: ", level, use_ansi)
        yield f"{branch}{repr(node)}"
        return
    elif not node:
        branch, _ = TREE_CONTINUE if through else TREE_LAST
        branch = maybe_ansi(f"{branch} {header}: ", level, use_ansi)
        yield f"{branch}[]"
        return
    else:
        header += "[{0}]: "

    for index, item in enumerate(node):
        branch, stalk = TREE_LAST if index == len(node) - 1 and not through else TREE_CONTINUE
        branch, stalk = (
            maybe_ansi(f"{branch} {header}", level, use_ansi),
            maybe_ansi(stalk, level, use_ansi)
        )

        for child_index, description in enumerate(format_ast_node(item, level=level + 1, use_ansi=use_ansi)):
            if child_index == 0:
                yield f"{branch.format(index)}{description}"
            else:
                yield f"{stalk + (' ' * len(header.format(index)))} {description}"


def format_ast_node(node: typing.Optional[ast.AST], level: int = 0, use_ansi: bool = True) -> typing.Generator[str, None, None]:
    """
    Recursively formats an AST node structure

    The code for this is pretty disgusting as it is, to be honest
    Serious refactoring consideration required here.
    """

    if isinstance(node, ast.AST):
        if use_ansi:
            yield f"\u001b[{(level % 6) + 31}m{type(node).__name__}\u001b[0m"
        else:
            yield type(node).__name__

        fields = node._fields

        for index, field in enumerate(fields):
            yield from format_ast_block(
                getattr(node, field),
                header=field,
                through=index < len(fields) - 1,
                level=level,
                use_ansi=use_ansi
            )

    else:
        if use_ansi:
            yield f"\u001b[1;4m{repr(node)}\u001b[0m"
        else:
            yield repr(node)


def create_tree(code: str, use_ansi: bool = True) -> str:
    """
    Compiles code into an AST tree and then formats it
    """

    user_code = import_expression.parse(code, mode='exec')  # type: ignore
    return '\n'.join(format_ast_node(user_code, use_ansi=use_ansi))
