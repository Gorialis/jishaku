# -*- coding: utf-8 -*-

"""
jishaku.repl.repl_builtins
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Builtin functions and variables within Jishaku REPL contexts.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import typing

import aiohttp
import discord

from jishaku.types import ContextA


async def http_get_bytes(*args: typing.Any, **kwargs: typing.Any) -> bytes:
    """
    Performs a HTTP GET request against a URL, returning the response payload as bytes.

    The arguments to pass are the same as :func:`aiohttp.ClientSession.get`.
    """

    async with aiohttp.ClientSession() as session:
        async with session.get(*args, **kwargs) as response:
            response.raise_for_status()

            return await response.read()


async def http_get_json(*args: typing.Any, **kwargs: typing.Any) -> typing.Dict[typing.Any, typing.Any]:
    """
    Performs a HTTP GET request against a URL,
    returning the response payload as a dictionary of the response payload interpreted as JSON.

    The arguments to pass are the same as :func:`aiohttp.ClientSession.get`.
    """

    async with aiohttp.ClientSession() as session:
        async with session.get(*args, **kwargs) as response:
            response.raise_for_status()

            return await response.json()


async def http_post_bytes(*args: typing.Any, **kwargs: typing.Any) -> bytes:
    """
    Performs a HTTP POST request against a URL, returning the response payload as bytes.

    The arguments to pass are the same as :func:`aiohttp.ClientSession.post`.
    """

    async with aiohttp.ClientSession() as session:
        async with session.post(*args, **kwargs) as response:
            response.raise_for_status()

            return await response.read()


async def http_post_json(*args: typing.Any, **kwargs: typing.Any) -> typing.Dict[typing.Any, typing.Any]:
    """
    Performs a HTTP POST request against a URL,
    returning the response payload as a dictionary of the response payload interpreted as JSON.

    The arguments to pass are the same as :func:`aiohttp.ClientSession.post`.
    """

    async with aiohttp.ClientSession() as session:
        async with session.post(*args, **kwargs) as response:
            response.raise_for_status()

            return await response.json()


def get_var_dict_from_ctx(ctx: ContextA, prefix: str = '_') -> typing.Dict[str, typing.Any]:
    """
    Returns the dict to be used in REPL for a given Context.
    """

    raw_var_dict = {
        'author': ctx.author,
        'bot': ctx.bot,
        'channel': ctx.channel,
        'ctx': ctx,
        'find': discord.utils.find,
        'get': discord.utils.get,
        'guild': ctx.guild,
        'me': ctx.me,
        'http_get_bytes': http_get_bytes,
        'http_get_json': http_get_json,
        'http_post_bytes': http_post_bytes,
        'http_post_json': http_post_json,
        'message': ctx.message,
        'msg': ctx.message
    }

    return {f'{prefix}{k}': v for k, v in raw_var_dict.items()}
