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
import inspect
import os
import re
import shlex
import subprocess
import time
import traceback


SEMICOLON_LOOKAROUND = re.compile("(?!\B[\"'][^\"']*);(?![^\"']*[\"']\B)")


class Jishaku:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_time = time.monotonic()
        self.repl_global_scope = {}
        self.repl_local_scope = {}

    @staticmethod
    async def do_after_sleep(delay: float, coro, *args, **kwargs):
        await asyncio.sleep(delay)
        return await coro(*args, **kwargs)

    def do_later(self, delay: float, coro, *args, **kwargs):
        return self.bot.loop.create_task(self.do_after_sleep(delay, coro, *args, **kwargs))

    @commands.group(name="jishaku", aliases=["jsk"])
    @commands.is_owner()
    async def jsk(self, ctx):
        """Jishaku debug and diagnostic commands

        This command on its own does nothing, all functionality is in subcommands.
        """

        pass

    @jsk.command(name="selftest")
    async def self_test(self, ctx):
        """Jishaku self-test

        This tests that Jishaku and the bot are functioning correctly.
        """

        current_time = time.monotonic()
        time_string = utils.humanize_relative_time(self.init_time - current_time)
        await ctx.send(f"Jishaku running, init {time_string}.\n"
                       f"This bot can see {len(self.bot.guilds)} guilds, {len(self.bot.users)} users.")

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
        await self.repl_backend(ctx, code)

    @jsk.command(name="python_what", aliases=["py_what", "pyw"])
    async def python_what(self, ctx, *, code: str):
        """Returns info on the result of an evaluated expression

        This evaluates the code passed into it and gives info on the result.
        """
        code = utils.cleanup_codeblock(code)
        await self.py_what_backend(ctx, code)

    async def repl_inner_backend(self, ctx: commands.Context, code: str):
        """Attempts to compile code and execute it."""

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

        # Await it with local scope args
        return await extracted_coro(ctx)

    async def repl_backend(self, ctx: commands.Context, code: str):
        """Passes code into the repl backend, and handles the result or resulting exceptions."""
        # create handle that'll add a right arrow reaction if this execution takes a long time
        handle = self.do_later(1, self.attempt_add_reaction, ctx.message, "\N{BLACK RIGHT-POINTING TRIANGLE}")

        try:
            result = await self.repl_inner_backend(ctx, code)
        except SyntaxError as exc:
            handle.cancel()
            await self.attempt_add_reaction(ctx.message, "\N{HEAVY EXCLAMATION MARK SYMBOL}")
            await self.repl_handle_syntaxerror(ctx, exc)
            return
        except Exception as exc:
            handle.cancel()
            await self.attempt_add_reaction(ctx.message, "\N{DOUBLE EXCLAMATION MARK}")
            await self.repl_handle_exception(ctx, exc)
        else:
            if result is None:
                handle.cancel()
                await self.attempt_add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")
                return

            if not isinstance(result, str):
                # repr all non-strings
                result = repr(result)

            # if result is really long cut it down
            if len(result) > 1995:
                result = result[0:1995] + "..."
            handle.cancel()
            await ctx.send(result)
            await self.attempt_add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")

    async def py_what_backend(self, ctx: commands.Context, code: str):
        """Evaluate code similar to above, but examine it instead of returning it"""
        # create handle that'll add a right arrow reaction if this execution takes a long time
        handle = self.do_later(1, self.attempt_add_reaction, ctx.message, "\N{BLACK RIGHT-POINTING TRIANGLE}")

        try:
            result = await self.repl_inner_backend(ctx, code)
        except SyntaxError as exc:
            handle.cancel()
            await self.attempt_add_reaction(ctx.message, "\N{HEAVY EXCLAMATION MARK SYMBOL}")
            await self.repl_handle_syntaxerror(ctx, exc)
            return
        except Exception as exc:
            handle.cancel()
            await self.attempt_add_reaction(ctx.message, "\N{DOUBLE EXCLAMATION MARK}")
            await self.repl_handle_exception(ctx, exc)
        else:
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

            handle.cancel()
            await ctx.send(summary)

    @staticmethod
    async def repl_handle_exception(ctx, exc: Exception):
        """Handles exec exceptions.

        This tries to DM the author with the traceback."""
        traceback_content = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 8))
        if len(traceback_content) > 1985:
            traceback_content = "..." + traceback_content[-1985:]
        await ctx.author.send(f"```py\n{traceback_content}\n```")

    @staticmethod
    async def repl_handle_syntaxerror(ctx, exc: SyntaxError):
        """Handles and points to syntax errors.

        We handle this differently from normal exceptions since we don't need a long traceback.
        """

        traceback_content = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 0))
        await ctx.send(f"```py\n{traceback_content}\n```")

    @staticmethod
    async def attempt_add_reaction(msg: discord.Message, text: str):
        """Try to add a reaction, ignore if it fails"""
        try:
            await msg.add_reaction(text)
        except discord.HTTPException:
            pass

    def sh_backend(self, code):
        """Open a subprocess, wait for it and format the output"""
        if os.name == "nt":
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

        # create handle that'll add a right arrow reaction if this execution takes a long time
        handle = self.do_later(1, self.attempt_add_reaction, ctx.message, "\N{BLACK RIGHT-POINTING TRIANGLE}")
        try:
            result = await self.bot.loop.run_in_executor(None, self.sh_backend, code)
        except subprocess.TimeoutExpired:
            # the subprocess took more than 30 seconds to execute
            # this could be because it was busy or because it blocked waiting for input

            # cancel the arrow reaction handle
            handle.cancel()
            # add an alarm clock reaction
            await self.attempt_add_reaction(ctx.message, "\N{ALARM CLOCK}")
        except Exception as exc:
            # something went wrong trying to create the subprocess

            # cancel the arrow reaction handle
            handle.cancel()
            # add !! emote
            await self.attempt_add_reaction(ctx.message, "\N{DOUBLE EXCLAMATION MARK}")
            # handle this the same as a standard repl exception
            await self.repl_handle_exception(ctx, exc)
        else:
            # nothing went wrong

            # cancel the arrow reaction handle
            handle.cancel()
            # :tick:
            await self.attempt_add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")
            # send the result of the command
            await ctx.send(result)

    @jsk.command(name="git")
    async def git_command(self, ctx: commands.Context, *, code: str):
        """Uses sh to make calls to git

        Equivalent to 'sh git <code>'.
        """
        await ctx.invoke(self.sh_command, code=' '.join(['git', code]))

    @jsk.command(name="load")
    async def load_command(self, ctx: commands.Context, *args: str):
        """Load a discord.py extension."""
        # this list contains the info we'll output at the end
        formatting_list = []
        # the amount of exts trying to load that succeeded
        success_count = 0
        total_count = len(args)

        for ext_name in args:
            try:
                self.bot.load_extension(ext_name)
            except Exception as exc:
                # add the extension name, exception type and exception string truncated
                exception_text = str(exc)
                formatting_list.append(f"- {ext_name}\n! {exc.__class__.__name__}: {exception_text:.75}")
                continue
            else:
                formatting_list.append(f"+ {ext_name}")
                success_count += 1

        full_list = "\n\n".join(formatting_list)
        await ctx.send(f"{success_count}/{total_count} loaded successfully\n```diff\n{full_list}\n```")

    @jsk.command(name="unload")
    async def unload_command(self, ctx: commands.Context, *args: str):
        """Unload a discord.py extension."""
        # this list contains the info we'll output at the end
        formatting_list = []
        # the amount of exts trying to unload that succeeded
        success_count = 0
        total_count = len(args)

        for ext_name in args:
            try:
                self.bot.unload_extension(ext_name)
            except Exception as exc:
                # add the extension name, exception type and exception string truncated
                exception_text = str(exc)
                formatting_list.append(f"- {ext_name}\n! {exc.__class__.__name__}: {exception_text:.75}")
                continue
            else:
                formatting_list.append(f"+ {ext_name}")
                success_count += 1

        full_list = "\n\n".join(formatting_list)
        await ctx.send(f"{success_count}/{total_count} unloaded successfully\n```diff\n{full_list}\n```")

    @jsk.command(name="reload")
    async def reload_command(self, ctx: commands.Context, *args: str):
        """Reload a discord.py extension."""
        # this list contains the info we'll output at the end
        formatting_list = []
        # the amount of exts trying to reload that succeeded
        success_count = 0
        total_count = len(args)

        for ext_name in args:
            try:
                self.bot.unload_extension(ext_name)
                self.bot.load_extension(ext_name)
            except Exception as exc:
                # add the extension name, exception type and exception string truncated
                exception_text = str(exc)
                formatting_list.append(f"- {ext_name}\n! {exc.__class__.__name__}: {exception_text:.75}")
                continue
            else:
                formatting_list.append(f"+ {ext_name}")
                success_count += 1

        full_list = "\n\n".join(formatting_list)
        await ctx.send(f"{success_count}/{total_count} reloaded successfully\n```diff\n{full_list}\n```")

    @jsk.command(name="selfreload")
    async def self_reload_command(self, ctx: commands.Context):
        """Attempts to fully reload jishaku."""
        needs_reload = ["jishaku.utils", "jishaku.cog", "jishaku"]

        setcode = "\n".join(["import importlib", *[f"import {x}\nimportlib.reload({x})" for x in needs_reload]])
        exec(setcode, {}, {})

        self.bot.unload_extension("jishaku")
        self.bot.load_extension("jishaku")

        await ctx.send("Reload OK")
