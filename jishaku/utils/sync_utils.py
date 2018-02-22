# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2017 Devon R

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import re


__all__ = ("REPL_COROUTINE_FORMAT", "humanize_relative_time", "cleanup_codeblock", "clean_sh_content", "repl_coro")


REPL_COROUTINE_FORMAT = """
async def __repl_coroutine(_ctx):
    _msg = _ctx.message
    _message = _msg
    _guild = _ctx.guild
    _channel = _ctx.channel
    _author = _ctx.author

    {}
"""


def humanize_relative_time(seconds: int):
    """
    Converts an amount of time in seconds to a human-friendly format.
    :param seconds: The amount of seconds, relative to now.
    :return: The humanized string
    """
    # in case we get a float
    seconds = int(seconds)

    if seconds == 0:
        return 'now'  # negligible time distance

    if seconds < 0:
        seconds = abs(seconds)
        past = True  # append 'ago' when creating string
    else:
        past = False

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)

    seconds = round(seconds, 2)  # human-friendly numbers thanks

    units = (weeks, 'week'), (days, 'day'), (hours, 'hour'), (minutes, 'minute'), (seconds, 'second')

    formatted_unit_list = []
    for measurement, unit in units:
        if not measurement:
            continue
        formatted_unit_list.append('{} {}'.format(measurement, unit + ('s' if measurement - 1 else '')))

    return ', '.join(formatted_unit_list) + (' ago' if past else '')


def cleanup_codeblock(code: str) -> str:
    """
    Attempts to remove surrounding codeblocks on eval code.
    :param code: The text to strip the codeblock from.
    :return: The stripped code.
    """
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    return code.strip("`\n")


def clean_sh_content(buffer: bytes) -> str:
    """
    Removes various control characters, such as colors, from CLI/sh output to make it into pure text.
    :param buffer: The bytes to clean
    :return: A string with the control characters removed.
    """
    # decode the bytestring and strip any extra data we don't care for
    text = buffer.decode('utf8').replace('\r', '').strip('\n')
    # remove color-code characters, escape backticks and strip again for good measure
    return re.sub(r'\x1b[^m]*m', '', text).replace("``", "`\u200b`").strip('\n')


def repl_coro(code: str) -> str:
    """
    Wraps async code in an async function so it can be compiled.
    :param code: The async code to encapsulate
    :return: Code defining an async function of the supplied code
    """
    return REPL_COROUTINE_FORMAT.format("\n    ".join(code.split("\n")))
