# -*- coding: utf-8 -*-

"""
jishaku.inline_import
~~~~~~~~~~~~~~~~~~~~~

Logic for parsing Python with inline import syntax.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import ast
import functools
import io
import sys
import tokenize
import typing

if typing.TYPE_CHECKING:
    from typing_extensions import Buffer as ReadableBuffer
    from typing_extensions import ParamSpec
    P = ParamSpec("P")
else:
    ReadableBuffer = bytes
    P = [typing.TypeVar("P")]

T = typing.TypeVar("T")


__all__ = ("parse",)


# ======== Token modification.


def offset_token_horizontal(tok: tokenize.TokenInfo, offset: int) -> tokenize.TokenInfo:
    """Takes a token and returns a new token with the columns for start and end offset by a given amount."""

    start_row, start_col = tok.start
    end_row, end_col = tok.end
    return tok._replace(start=(start_row, start_col + offset), end=(end_row, end_col + offset))


def offset_line_horizontal(
    tokens: typing.List[tokenize.TokenInfo],
    start_index: int = 0,
    *,
    line: int,
    offset: int,
) -> None:
    """Takes a list of tokens and changes the offset of some of the tokens in place."""

    for i, tok in enumerate(tokens[start_index:], start=start_index):
        if tok.start[0] != line:
            break
        tokens[i] = offset_token_horizontal(tok, offset)


def transform_tokens(tokens: typing.Iterable[tokenize.TokenInfo]) -> typing.List[tokenize.TokenInfo]:
    """Find the inline import expressions in a list of tokens and replace the relevant tokens to wrap the imported
    modules with '_IMPORTLIB_MARKER(...)'.

    Later, the AST transformer step will replace those with valid import expressions.
    """

    orig_tokens = list(tokens)
    new_tokens: typing.List[tokenize.TokenInfo] = []

    for orig_i, tok in enumerate(orig_tokens):
        # "!" is only an OP in >=3.12.
        if tok.type in {tokenize.OP, tokenize.ERRORTOKEN} and tok.string == "!":
            has_invalid_syntax = False

            # Collect all name and attribute access-related tokens directly connected to the "!".
            last_place = len(new_tokens)
            looking_for_name = True

            for old_tok in reversed(new_tokens):
                if old_tok.exact_type != (tokenize.NAME if looking_for_name else tokenize.DOT):
                    # The "!" was placed somewhere in a class definition, e.g. "class Fo!o: pass".
                    has_invalid_syntax = (old_tok.exact_type == tokenize.NAME and old_tok.string == "class")

                    # There's a name immediately following "!". Might be a f-string conversion flag
                    # like "f'{thing!r}'" or just something invalid like "def fo!o(): pass".
                    try:
                        peek = orig_tokens[orig_i + 1]
                    except IndexError:
                        pass
                    else:
                        has_invalid_syntax = (has_invalid_syntax or peek.type == tokenize.NAME)

                    break

                last_place -= 1
                looking_for_name = not looking_for_name

            # The "!" is just by itself or in a bad spot. Let it error later if it's wrong.
            # Also allows other token transformers to work with it without erroring early.
            if has_invalid_syntax or last_place == len(new_tokens):
                new_tokens.append(tok)
                continue

            # Insert "_IMPORTLIB_MARKER(" just before the inline import expression.
            old_first = new_tokens[last_place]
            old_f_row, old_f_col = old_first.start

            new_tokens[last_place:last_place] = [
                old_first._replace(type=tokenize.NAME, string="_IMPORTLIB_MARKER", end=(old_f_row, old_f_col + 17)),
                tokenize.TokenInfo(
                    tokenize.OP,
                    "(",
                    (old_f_row, old_f_col + 17),
                    (old_f_row, old_f_col + 18),
                    old_first.line,
                ),
            ]

            # Adjust the positions of the following tokens within the inline import expression.
            new_tokens[last_place + 2:] = (offset_token_horizontal(tok, 18) for tok in new_tokens[last_place + 2:])

            # Add a closing parenthesis.
            (end_row, end_col) = new_tokens[-1].end
            line = new_tokens[-1].line
            end_paren_token = tokenize.TokenInfo(tokenize.OP, ")", (end_row, end_col), (end_row, end_col + 1), line)
            new_tokens.append(end_paren_token)

            # Fix the positions of the rest of the tokens on the same line.
            fixed_line_tokens: typing.List[tokenize.TokenInfo] = []
            offset_line_horizontal(orig_tokens, orig_i, line=new_tokens[-1].start[0], offset=18)

            # Check the rest of the line for inline import expressions.
            new_tokens.extend(transform_tokens(fixed_line_tokens))

        else:
            new_tokens.append(tok)

    # Hack to get around a bug where code that ends in a comment, but no newline, has an extra
    # NEWLINE token added in randomly. This patch wasn't backported to 3.8.
    # https://github.com/python/cpython/issues/79288
    # https://github.com/python/cpython/issues/88833
    if sys.version_info < (3, 9):
        if len(new_tokens) >= 4 and (
            new_tokens[-4].type == tokenize.COMMENT
            and new_tokens[-3].type == tokenize.NL
            and new_tokens[-2].type == tokenize.NEWLINE
            and new_tokens[-1].type == tokenize.ENDMARKER
        ):
            del new_tokens[-2]

    return new_tokens


def transform_source(source: typing.Union[str, ReadableBuffer]) -> str:
    """Replace and wrap inline import expressions in source code so that it has syntax, with explicit markers for
    where to perform the imports.
    """

    if isinstance(source, str):
        source = source.encode("utf-8")
    stream = io.BytesIO(source)
    encoding, _ = tokenize.detect_encoding(stream.readline)
    stream.seek(0)
    tokens_list = transform_tokens(tokenize.tokenize(stream.readline))
    try:
        if tokens_list[1].type == tokenize.COMMENT:
            import pprint
            pprint.pprint(tokens_list)
    except IndexError:
        pass
    return tokenize.untokenize(tokens_list).decode(encoding)


# ======== AST modification.


class InlineImportTransformer(ast.NodeTransformer):
    """An AST transformer that replaces '_IMPORTLIB_MARKER(...)' with '__import__("importlib").import_module(...)'."""

    @classmethod
    def _collapse_attributes(cls, node: typing.Union[ast.Attribute, ast.Name]) -> str:
        if isinstance(node, ast.Name):
            return node.id

        if not (
            isinstance(node, ast.Attribute)  # pyright: ignore[reportUnnecessaryIsInstance]
            and isinstance(node.value, (ast.Attribute, ast.Name))
        ):
            msg = "Only names and attribute access (dot operator) can be within the inline import expression."
            raise SyntaxError(msg)  # noqa: TRY004

        return cls._collapse_attributes(node.value) + f".{node.attr}"

    def visit_Call(self, node: ast.Call) -> ast.AST:
        """Replace the _IMPORTLIB_MARKER calls with a valid inline import expression."""

        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "_IMPORTLIB_MARKER"
            and len(node.args) == 1
            and isinstance(node.args[0], (ast.Attribute, ast.Name))
        ):
            node.func = ast.Attribute(
                value=ast.Call(
                    func=ast.Name(id="__import__", ctx=ast.Load()),
                    args=[ast.Constant(value="importlib")],
                    keywords=[],
                ),
                attr="import_module",
                ctx=ast.Load(),
            )
            node.args[0] = ast.Constant(value=self._collapse_attributes(node.args[0]))

        return self.generic_visit(node)


def transform_ast(tree: ast.AST) -> ast.Module:
    """Walk through an AST and fix it to turn the _IMPORTLIB_MARKER(...) expressions into valid import statements."""

    return ast.fix_missing_locations(InlineImportTransformer().visit(tree))


def copy_annotations(original_func: typing.Callable[P, T]) -> typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]:
    """Overrides annotations, thus lying, but it works for the final annotations that the *user* sees on the decorated func."""

    @functools.wraps(original_func)
    def inner(new_func: typing.Callable[P, T]) -> typing.Callable[P, T]:
        return new_func

    return inner


# Some of the parameter annotations are too narrow or wide, but they should be "overriden" by this decorator.
@copy_annotations(ast.parse)  # type: ignore
def parse(
    source: typing.Union[str, ReadableBuffer],
    filename: str = "<unknown>",
    mode: str = "exec",
    *,
    type_comments: bool = False,
    feature_version: typing.Optional[typing.Tuple[int, int]] = None,
) -> ast.Module:
    """Convert source code with inline import expressions to an AST. Has the same signature as ast.parse."""

    return transform_ast(
        ast.parse(
            transform_source(source),
            filename,
            mode,
            type_comments=type_comments,
            feature_version=feature_version,
        )
    )
