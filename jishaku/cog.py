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

from . import utils

import discord
from discord.ext import commands

import asyncio
import functools
import inspect
import os
import re
import shlex
import subprocess
import sys
import time
import typing


SEMICOLON_LOOKAROUND = re.compile("(?!\B[\"'][^\"']*);(?![^\"']*[\"']\B)")

HIDE_JISHAKU = os.getenv("JISHAKU_HIDE", "").lower() in ('true', 't', 'yes', 'y', 'on', '1')


class Jishaku:
    """
    Class that contains the Jishaku command, subcommands, and various context-sensitive utilities Jishaku uses.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_time = time.monotonic()
        self.repl_global_scope = {}
        self.repl_local_scope = {}

    def do_later(self, delay: float, coro, *args, **kwargs):
        """
        Sync interface to return a task for do_after_sleep
        Like loop.call_later, but for coroutines.
        Useful to create cancellable deferred tasks.

        :param delay: Time in seconds
        :param coro: Coroutine to run
        :param args: Arguments to pass to coroutine
        :param kwargs: Keyword arguments to pass to coroutine
        :return: Cancellable task for the coroutine
        """
        return self.bot.loop.create_task(utils.do_after_sleep(delay, coro, *args, **kwargs))

    @commands.group(name="jishaku", aliases=["jsk"], hidden=HIDE_JISHAKU)
    @commands.is_owner()
    async def jsk(self, ctx):
        """Jishaku debug and diagnostic commands

        This command on its own does nothing, all functionality is in subcommands.
        """

        pass

    @jsk.command(name="selftest", aliases=["self_test", "self-test"])
    async def self_test(self, ctx):
        """
        Jishaku self-test

        This tests that Jishaku and the bot are functioning correctly.
        """

        current_time = time.monotonic()
        time_string = utils.humanize_relative_time(self.init_time - current_time)
        await ctx.send(f"Jishaku running, init {time_string}.\n"
                       f"This bot can see {len(self.bot.guilds)} guilds, {len(self.bot.users)} users.")

    @jsk.command(name="hide")
    async def hide_self(self, ctx):
        """Hides the Jishaku command from help."""
        if self.jsk.hidden:
            return await ctx.send("Already hidden.")

        self.jsk.hidden = True
        await ctx.send("Hiding away..")

    @jsk.command(name="show")
    async def show_self(self, ctx):
        """Shows the Jishaku command in help."""
        if not self.jsk.hidden:
            return await ctx.send("Already visible.")

        self.jsk.hidden = False
        await ctx.send("Showing self..")

    def prepare_environment(self, ctx: commands.Context):
        """Update the REPL scope with variables relating to the current ctx"""
        self.repl_global_scope.update({
            "_bot": ctx.bot,
            "asyncio": asyncio,
            "discord": discord
        })

    @jsk.command(name="python", aliases=["py", "```py"])
    async def python_repl(self, ctx, *, code: str):
        """Python REPL-like command

        This evaluates or executes code passed into it, supporting async syntax.
        Global variables include _ctx and _bot for interactions.
        """

        code = utils.cleanup_codeblock(code)

        async with utils.ReplResponseReactor(ctx.message):
            await self.repl_backend(ctx, code, self.py_callback)

    @jsk.command(name="python_what", aliases=["py_what", "pyw"])
    async def python_what(self, ctx, *, code: str):
        """Returns info on the result of an evaluated expression

        This evaluates the code passed into it and gives info on the result.
        """
        code = utils.cleanup_codeblock(code)

        async with utils.ReplResponseReactor(ctx.message):
            await self.repl_backend(ctx, code, self.pyw_callback)

    async def repl_backend(self, ctx: commands.Context, code: str, callback):
        """
        Attempt to compile and execute code, yielding results to a callback.
        :param ctx: Context for the repl environment and callback.
        :param code: Code to try and execute
        :param callback: Callback to send all results to.
        :return: The final result, if there was one.
        """

        if "\n" not in code and not any(SEMICOLON_LOOKAROUND.findall(code)):
            # if there are no line breaks and no semicolons try eval mode first
            with_return = ' '.join(['return', code])

            try:
                # try to compile with 'return' in front first
                # this lets you do eval-like expressions
                coro_format = utils.repl_coro(with_return)
                code_object = compile(coro_format, '<repl-v session>', 'exec')
            except SyntaxError:
                code_object = None
        else:
            code_object = None

        # we set as None and check here because nesting looks worse and complicates the traceback
        # if this code fails.

        if code_object is None:
            coro_format = utils.repl_coro(code)
            code_object = compile(coro_format, '<repl-x session>', 'exec')

        # our code object is ready, let's actually execute it now
        self.prepare_environment(ctx)

        exec(code_object, self.repl_global_scope, self.repl_local_scope)

        # Grab the coro we just defined
        extracted_coro = self.repl_local_scope.get("__repl_coroutine")

        result = None

        # Allow async generator definitions for multiple-result yielding
        if inspect.isasyncgenfunction(extracted_coro):
            # For every result we get back,
            async for result in extracted_coro(ctx):
                # send it to the callback.
                await callback(ctx, result)
        else:
            # Not an async generator, so await with local scope args
            result = await extracted_coro(ctx)
            await callback(ctx, result)

        return result

    @staticmethod
    async def py_callback(ctx: commands.Context, result) -> typing.Optional[discord.Message]:
        """
        Callback that converts the result into a chat-compatible format and sends it to the chat.
        :param ctx: Context, passed by caller
        :param result: The object to be converted
        :return: The message sent
        """

        if result is not None:
            if isinstance(result, discord.File):
                return await ctx.send(file=result)

            if not isinstance(result, str):
                # repr all non-strings
                result = repr(result)

            if len(result) > 1995:
                # if result is really long cut it down
                result = result[0:1995] + "..."
            elif result.strip() == '':
                # or if it's literally empty replace with a zwsp
                result = '\u200b'

            return await ctx.send(result)

    @staticmethod
    async def pyw_callback(ctx: commands.Context, result) -> discord.Message:
        """
        Callback that examines the result and sends information on it to the channel.
        :param ctx: Context, passed by caller
        :param result: The object to be examined
        :return: The message sent
        """
        information = []

        header = repr(result).replace('`', '\u200b`')
        if len(header) > 485:
            header = header[0:482] + '...'

        information.append(('Type', type(result).__name__))
        information.append(('Memory Location', hex(id(result))))

        try:
            information.append(('Module Name', inspect.getmodule(result).__name__))
        except (TypeError, AttributeError):
            pass

        try:
            file_loc = inspect.getfile(result)
        except TypeError:
            pass
        else:
            cwd = os.getcwd()
            if file_loc.startswith(cwd):
                file_loc = "." + file_loc[len(cwd):]
            information.append(('File Location', file_loc))

        try:
            source_lines, source_offset = inspect.getsourcelines(result)
        except TypeError:
            pass
        else:
            information.append(('Line Span', f'{source_offset}-{source_offset+len(source_lines)}'))

        try:
            signature = inspect.signature(result)
        except (TypeError, AttributeError, ValueError):
            pass
        else:
            information.append(('Signature', str(signature)))

        if inspect.isclass(result):
            try:
                information.append(('Class MRO', ', '.join([x.__name__ for x in inspect.getmro(result)])))
            except (TypeError, AttributeError):
                pass

        if isinstance(result, (str, tuple, list, bytes)):
            information.append(('Length', len(result)))

        information_flatten = "\n".join(f"{x:16.16} :: {y}" for x, y in information)
        summary = f"```prolog\n== {header} ==\n\n{information_flatten}\n```"

        return await ctx.send(summary)

    @staticmethod
    def sh_backend(code):
        """Open a subprocess, wait for it and format the output"""
        if sys.platform == "win32":
            sequence = shlex.split(code)
        else:
            sequence = ["/bin/bash", "-c", code]
        with subprocess.Popen(sequence, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            out, err = map(utils.clean_sh_content, process.communicate(timeout=30))

        # if this includes some stderr as well as stdout
        if err:
            out = out or '\u200b'
            total_length = len(out) + len(err)

            # if the whole thing won't fit in a message
            if total_length > 1968:
                # scale stdout and stderr to their proportions within a message
                out_resize_len = len(out) * (1960 / total_length)
                err_resize_len = len(err) * (1960 / total_length)

                # add ellipses to show these have been truncated
                # we show the last x amount of characters since they're usually the most important
                out = "...\n" + out[int(-out_resize_len):].strip()
                err = "...\n" + err[int(-err_resize_len):].strip()

            # format into codeblocks
            return f"```prolog\n{out}\n```\n```prolog\n{err}\n```"
        else:
            # if the stdout won't fit in a message
            if len(out) > 1980:
                out = "...\n" + out[-1980:].strip()
            # format into a single codeblock
            return f"```prolog\n{out}\n```"

    @jsk.command(name="sh", aliases=["```sh"])
    async def sh_command(self, ctx: commands.Context, *, code: str):
        """Use the shell to run other CLI programs

        This supports invoking programs, but not other shell syntax.
        """

        code = utils.cleanup_codeblock(code)

        async with utils.ReplResponseReactor(ctx.message) as handler:
            result = await self.bot.loop.run_in_executor(None, self.sh_backend, code)

        if not handler.raised:
            # nothing went wrong

            # send the result of the command
            await ctx.send(result)

    @jsk.command(name="git")
    async def git_command(self, ctx: commands.Context, *, code: str):
        """Uses sh to make calls to git

        Equivalent to 'sh git <code>'.
        """
        await ctx.invoke(self.sh_command, code=' '.join(['git', code]))

    @staticmethod
    def try_multiple(operations, *args, **kwargs) -> typing.Optional[Exception]:
        """
        Does multiple operations on a set of arguments, returning an exception if there was one.
        :param operations: Iterable of operations to perform
        :param args: Arguments to pass to each operation
        :param kwargs: Keyword arguments to pass to each operation
        :return: The exception object, if there was one.
        """
        try:
            for operation in operations:
                operation(*args, **kwargs)
        except Exception as exc:
            return exc

    def format_extension_management(self, operations, extension_name) -> str:
        """
        Does operations with an extension name, returning a difflist entry based on whether it succeeded.
        :param operations: Operations to perform (load_command, etc)
        :param extension_name: The extension name
        :return: Diff list entry
        """

        exception = self.try_multiple(operations, extension_name)
        if exception:
            return f"- \N{CROSS MARK} {extension_name}\n! {exception.__class__.__name__}: {exception!s:.75}"
        else:
            return f"+ \N{WHITE HEAVY CHECK MARK} {extension_name}"

    @jsk.command(name="load")
    async def load_command(self, ctx: commands.Context, *args: str):
        """Loads discord.py extensions."""

        formatted = '\n\n'.join(map(functools.partial(self.format_extension_management,
                                                      (self.bot.load_extension,)), args))

        await ctx.send(f"Attempted to load {len(args)} extension(s).\n```diff\n{formatted}\n```")

    @jsk.command(name="unload")
    async def unload_command(self, ctx: commands.Context, *args: str):
        """Unloads discord.py extensions."""

        formatted = '\n\n'.join(map(functools.partial(self.format_extension_management,
                                                      (self.bot.unload_extension,)), args))

        await ctx.send(f"Attempted to unload {len(args)} extension(s).\n```diff\n{formatted}\n```")

    @jsk.command(name="reload")
    async def reload_command(self, ctx: commands.Context, *args: str):
        """Reloads discord.py extensions."""

        formatted = '\n\n'.join(map(functools.partial(self.format_extension_management,
                                                      (self.bot.unload_extension, self.bot.load_extension)), args))

        await ctx.send(f"Attempted to reload {len(args)} extension(s).\n```diff\n{formatted}\n```")

    @jsk.command(name="selfreload", aliases=["self_reload", "self-reload"])
    async def self_reload_command(self, ctx: commands.Context):
        """Attempts to fully reload jishaku."""
        needs_reload = ["jishaku.utils.sync_utils", "jishaku.utils.async_utils", "jishaku.utils.class_utils",
                        "jishaku.utils", "jishaku.cog", "jishaku"]

        setcode = "\n".join(["import importlib", *[f"import {x}\nimportlib.reload({x})" for x in needs_reload]])
        exec(setcode, {}, {})

        self.bot.unload_extension("jishaku")
        self.bot.load_extension("jishaku")

        await ctx.send("Reload OK")
