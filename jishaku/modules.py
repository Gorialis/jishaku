# -*- coding: utf-8 -*-

"""
jishaku.modules
~~~~~~~~~~~~~~

Functions for managing and searching modules.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import importlib.metadata
import pathlib
import typing

import discord
from braceexpand import braceexpand
from discord.ext import commands

from jishaku.types import BotT, ContextA

__all__ = ('find_extensions_in', 'resolve_extensions', 'package_version', 'ExtensionConverter')


if typing.TYPE_CHECKING:
    UnbalancedBracesError = ValueError
else:
    from braceexpand import UnbalancedBracesError


if typing.TYPE_CHECKING or discord.version_info >= (2, 0, 0):
    _ExtensionConverterBase = commands.Converter[typing.List[str]]
else:
    _ExtensionConverterBase = commands.Converter


def find_extensions_in(path: typing.Union[str, pathlib.Path]) -> typing.List[str]:
    """
    Tries to find things that look like bot extensions in a directory.
    """

    if not isinstance(path, pathlib.Path):
        path = pathlib.Path(path)

    if not path.is_dir():
        return []

    extension_names: typing.List[str] = []

    # Find extensions directly in this folder
    for subpath in path.glob('*.py'):
        parts = subpath.with_suffix('').parts
        if parts[0] == '.':
            parts = parts[1:]

        extension_names.append('.'.join(parts))

    # Find extensions as subfolder modules
    for subpath in path.glob('*/__init__.py'):
        parts = subpath.parent.parts
        if parts[0] == '.':
            parts = parts[1:]

        extension_names.append('.'.join(parts))

    return extension_names


def resolve_extensions(bot: BotT, name: str) -> typing.List[str]:
    """
    Tries to resolve extension queries into a list of extension names.
    """

    exts: typing.List[str] = []
    for ext in braceexpand(name):
        if ext.endswith('.*'):
            module_parts = ext[:-2].split('.')
            path = pathlib.Path(*module_parts)
            exts.extend(find_extensions_in(path))
        elif ext == '~':
            exts.extend(bot.extensions)
        else:
            exts.append(ext)

    return exts


def package_version(package_name: str) -> typing.Optional[str]:
    """
    Returns package version as a string, or None if it couldn't be found.
    """

    try:
        return importlib.metadata.version(package_name)
    # ValueError if package_name was empty
    except (importlib.metadata.PackageNotFoundError, ValueError):
        return None


class ExtensionConverter(_ExtensionConverterBase):  # pylint: disable=too-few-public-methods
    """
    A converter interface for resolve_extensions to match extensions from users.
    """

    async def convert(
        self,
        ctx: ContextA,
        argument: str
    ) -> typing.List[str]:
        """
        Converts a name, glob, or brace expand of extensions into the list of extension names.
        """

        try:
            return resolve_extensions(ctx.bot, argument)
        except UnbalancedBracesError as exc:
            raise commands.BadArgument(str(exc))
