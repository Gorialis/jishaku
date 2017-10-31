# -*- coding: utf-8 -*-

from . import utils

import discord
from discord.ext import commands

import re
import subprocess
import time
import traceback


class Jishaku:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_time = time.monotonic()
        self.repl_global_scope = {}
        self.repl_local_scope = {}

    @commands.group(name="jishaku", aliases=["jsk"])
    @commands.is_owner()
    async def jsk(self, ctx):
        """Jishaku debug and diagnostic commands

        This command on its own does nothing, all functionality is in subcommands."""
        pass

    @jsk.command(name="selftest")
    async def self_test(self, ctx):
        """Jishaku self-test

        This tests that Jishaku and the bot are functioning correctly.
        """
        current_time = time.monotonic()
        time_string = utils.humanize_relative_time(self.init_time - current_time)
        await ctx.send(f"Jishaku running, init {time_string}.")

    def prepare_environment(self, ctx: commands.Context):
        """Update the REPL scope with variables relating to the current ctx"""
        self.repl_global_scope.update({
            "_bot": ctx.bot
        })

    @jsk.command("python", aliases=["py", "```py"])
    async def python_repl(self, ctx, *, code: str):
        code = utils.cleanup_codeblock(code)
        await self.repl_backend(ctx, code)

    async def repl_backend(self, ctx: commands.Context, code: str):
        """Attempts to compile code and execute it."""
        # create handle that'll add a right arrow reaction if this execution takes a long time
        handle = self.bot.loop.call_later(3, self.bot.loop.create_task,
                                          self.attempt_add_reaction(ctx.message, "\N{BLACK RIGHT-POINTING TRIANGLE}"))

        if "\n" not in code:
            # if there are no line breaks try eval mode first
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
            try:
                coro_format = utils.repl_coro(code)
                code_object = compile(coro_format, '<repl-x session>', 'exec')
            except SyntaxError as exc:
                handle.cancel()
                await self.attempt_add_reaction(ctx.message, "\N{HEAVY EXCLAMATION MARK SYMBOL}")
                await self.repl_handle_syntaxerror(ctx, exc)
                return

        # our code object is ready, let's actually execute it now
        self.prepare_environment(ctx)

        try:
            exec(code_object, self.repl_global_scope, self.repl_local_scope)

            # Grab the coro we just defined
            extracted_coro = self.repl_local_scope.get("__repl_coroutine")

            # Await it with local scope args
            result = await extracted_coro(ctx, ctx.message)
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

    @staticmethod
    async def repl_handle_exception(ctx, exc: Exception):
        """Handles exec exceptions.

        This tries to DM the author with the traceback."""
        traceback_content = "\n".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 8))
        await ctx.author.send(f"```py\n{traceback_content}\n```")

    @staticmethod
    async def repl_handle_syntaxerror(ctx, exc: SyntaxError):
        """Handles and points to syntax errors.

        We handle this differently from normal exceptions since we don't need a long traceback."""

        traceback_content = "\n".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 0))
        await ctx.send(f"```py\n{traceback_content}\n```")

    @staticmethod
    async def attempt_add_reaction(msg: discord.Message, text: str):
        try:
            await msg.add_reaction(text)
        except discord.HTTPException:
            pass

    @staticmethod
    def clean_sh_content(buffer: bytes):
        text = buffer.decode('utf8').replace('\r', '').strip('\n')
        return re.sub(r'\x1b[^m]*m', '', text).strip('\n')

    def sh_backend(self, *args):
        proc = subprocess.Popen(list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = map(self.clean_sh_content, proc.communicate(timeout=30))

        if err:
            out = out or '\u200b'
            total_length = len(out) + len(err)
            if total_length > 1968:
                out_resize_len = len(out) * (1960 / total_length)
                err_resize_len = len(err) * (1960 / total_length)
                out = "...\n" + out[-out_resize_len:]
                err = "...\n" + err[-err_resize_len:]
            return f"```prolog\n{out}\n```\n```prolog\n{err}\n```"
        else:
            if len(out) > 1980:
                out = "...\n" + out[-1980:]
            return f"```prolog\n{out}\n```"

    @jsk.command("sh")
    async def sh_command(self, ctx: commands.Context, *args: str):
        handle = self.bot.loop.call_later(3, self.bot.loop.create_task,
                                          self.attempt_add_reaction(ctx.message, "\N{BLACK RIGHT-POINTING TRIANGLE}"))
        try:
            result = await self.bot.loop.run_in_executor(None, self.sh_backend, *args)
        except subprocess.TimeoutExpired:
            handle.cancel()
            await self.attempt_add_reaction(ctx.message, "\N{ALARM CLOCK}")
        except Exception as exc:
            handle.cancel()
            await self.attempt_add_reaction(ctx.message, "\N{DOUBLE EXCLAMATION MARK}")
            await self.repl_handle_exception(ctx, exc)
        else:
            handle.cancel()
            await self.attempt_add_reaction(ctx.message, "\N{WHITE HEAVY CHECK MARK}")
            await ctx.send(result)
