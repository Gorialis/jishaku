# -*- coding: utf-8 -*-

"""
jishaku.cog
~~~~~~~~~~~

The Jishaku debugging and diagnostics cog.

:copyright: (c) 2018 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import collections
import contextlib
import datetime
import inspect
import os
import os.path
import re
import time
import traceback
import typing

import discord
import humanize
from discord.ext import commands

from jishaku.codeblocks import Codeblock, CodeblockConverter
from jishaku.exception_handling import ReplResponseReactor
from jishaku.meta import __version__
from jishaku.models import copy_context_with
from jishaku.paginators import FilePaginator, PaginatorInterface, WrappedPaginator
from jishaku.repl import AsyncCodeExecutor, Scope, all_inspections, get_var_dict_from_ctx
from jishaku.shell import ShellReader
from jishaku.voice import BasicYouTubeDLSource, connected_check, playing_check, vc_check, youtube_dl

__all__ = (
    "Jishaku",
    "setup"
)

HIDE_JISHAKU = os.getenv("JISHAKU_HIDE", "").lower() in ("true", "t", "yes", "y", "on", "1")


CommandTask = collections.namedtuple("CommandTask", "index ctx task")


class Jishaku:  # pylint: disable=too-many-public-methods
    """
    The cog that includes Jishaku's Discord-facing default functionality.
    """

    load_time = datetime.datetime.now()

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._scope = Scope()
        self.retain = False
        self.last_result = None
        self.start_time = datetime.datetime.now()
        self.tasks = collections.deque()
        self.task_count: int = 0

    @property
    def scope(self):
        """
        Gets a scope for use in REPL.

        If retention is on, this is the internal stored scope,
        otherwise it is always a new Scope.
        """

        if self.retain:
            return self._scope
        return Scope()

    @contextlib.contextmanager
    def submit(self, ctx: commands.Context):
        """
        A context-manager that submits the current task to jishaku's task list
        and removes it afterwards.

        Arguments
        ---------
        ctx: commands.Context
            A Context object used to derive information about this command task.
        """

        self.task_count += 1
        cmdtask = CommandTask(self.task_count, ctx, asyncio.Task.current_task())
        self.tasks.append(cmdtask)

        try:
            yield cmdtask
        finally:
            if cmdtask in self.tasks:
                self.tasks.remove(cmdtask)

    @commands.group(name="jishaku", aliases=["jsk"], hidden=HIDE_JISHAKU)
    @commands.is_owner()
    async def jsk(self, ctx: commands.Context):
        """
        The Jishaku debug and diagnostic commands.

        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """

        if ctx.invoked_subcommand is not None and ctx.invoked_subcommand is not self.jsk:
            return

        # This only runs when no subcommand has been invoked, so give a brief.
        await ctx.send(inspect.cleandoc(f"""
            Jishaku v{__version__} is active. ({len(self.bot.guilds)} guild(s), {len(self.bot.users)} user(s))
            Module load time: {humanize.naturaltime(self.load_time)}
            {'Using automatic sharding.' if isinstance(self.bot, discord.AutoShardedClient) else
             'Using manual sharding.' if self.bot.shard_count else
             'Not using sharding.'}
            Average websocket latency: {round(self.bot.latency * 1000, 2)}ms
        """))

    @jsk.command(name="hide")
    async def jsk_hide(self, ctx: commands.Context):
        """
        Hides Jishaku from the help command.
        """

        if self.jsk.hidden:
            return await ctx.send("Jishaku is already hidden.")

        self.jsk.hidden = True
        await ctx.send("Jishaku is now hidden.")

    @jsk.command(name="show")
    async def jsk_show(self, ctx: commands.Context):
        """
        Shows Jishaku in the help command.
        """

        if not self.jsk.hidden:
            return await ctx.send("Jishaku is already visible.")

        self.jsk.hidden = False
        await ctx.send("Jishaku is now visible.")

    __cat_line_regex = re.compile(r"(?:\.\/+)?(.+?)(?:#L?(\d+)(?:\-L?(\d+))?)?$")

    @jsk.command(name="cat")
    async def jsk_cat(self, ctx: commands.Context, argument: str):
        """
        Read out a file, using syntax highlighting if detected.

        Lines and linespans are supported by adding '#L12' or '#L12-14' etc to the end of the filename.
        """

        match = self.__cat_line_regex.search(argument)

        if not match:  # should never happen
            return await ctx.send("Couldn't parse this input.")

        path = match.group(1)

        line_span = None

        if match.group(2):
            start = int(match.group(2))
            line_span = (start, int(match.group(3) or start))

        if not os.path.exists(path) or os.path.isdir(path):
            return await ctx.send(f"`{path}`: No file by that name.")

        size = os.path.getsize(path)

        if size <= 0:
            return await ctx.send(f"`{path}`: Cowardly refusing to read a file with no size stat"
                                  f" (it may be empty, endless or inaccessible).")

        if size > 50 * (1024 ** 2):
            return await ctx.send(f"`{path}`: Cowardly refusing to read a file >50MB.")

        try:
            with open(path, "rb") as file:
                paginator = FilePaginator(file, line_span=line_span, max_size=1985)
        except UnicodeDecodeError:
            return await ctx.send(f"`{path}`: Couldn't determine the encoding of this file.")
        except ValueError as exc:
            return await ctx.send(f"`{path}`: Couldn't read this file, {exc}")

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        await interface.send_to(ctx)

    @jsk.command(name="tasks")
    async def jsk_tasks(self, ctx: commands.Context):
        """
        Shows the currently running jishaku tasks.
        """

        if not self.tasks:
            return await ctx.send("No currently running tasks.")

        paginator = commands.Paginator(max_size=1985)

        for task in self.tasks:
            paginator.add_line(f"{task.index}: `{task.ctx.command.qualified_name}`, invoked at "
                               f"{task.ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        await interface.send_to(ctx)

    @jsk.command(name="cancel")
    async def jsk_cancel(self, ctx: commands.Context, *, index: int):
        """
        Cancels a task with the given index.

        If the index passed is -1, will cancel the last task instead.
        """

        if not self.tasks:
            return await ctx.send("No tasks to cancel.")

        if index == -1:
            task = self.tasks.pop()
        else:
            task = discord.utils.get(self.tasks, index=index)
            if task:
                self.tasks.remove(task)
            else:
                return await ctx.send("Unknown task.")

        task.task.cancel()
        return await ctx.send(f"Cancelled task {task.index}: `{task.ctx.command.qualified_name}`,"
                              f" invoked at {task.ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    @jsk.command(name="retain")
    async def jsk_retain(self, ctx: commands.Context, *, toggle: bool):
        """
        Turn variable retention for REPL on or off.
        """

        if toggle:
            if self.retain:
                return await ctx.send("Variable retention is already set to ON.")

            self.retain = True
            self._scope = Scope()
            return await ctx.send("Variable retention is ON. Future REPL sessions will retain their scope.")

        if not self.retain:
            return await ctx.send("Variable retention is already set to OFF.")

        self.retain = False
        return await ctx.send("Variable retention is OFF. Future REPL sessions will dispose their scope when done.")

    @jsk.command(name="py", aliases=["python"])
    async def jsk_python(self, ctx: commands.Context, *, argument: CodeblockConverter):
        """
        Direct evaluation of Python code.
        """

        arg_dict = get_var_dict_from_ctx(ctx)

        scope = self.scope

        scope.clean()
        arg_dict["_"] = self.last_result

        async with ReplResponseReactor(ctx.message):
            with self.submit(ctx):
                async for result in AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict):
                    if result is None:
                        continue

                    self.last_result = result

                    if isinstance(result, discord.File):
                        await ctx.send(file=result)
                    elif isinstance(result, discord.Embed):
                        await ctx.send(embed=result)
                    elif isinstance(result, PaginatorInterface):
                        await result.send_to(ctx)
                    else:
                        if not isinstance(result, str):
                            # repr all non-strings
                            result = repr(result)

                        if len(result) > 2000:
                            # inconsistency here, results get wrapped in codeblocks when they are too large
                            #  but don't if they're not. probably not that bad, but noting for later review
                            paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1985)

                            paginator.add_line(result)

                            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                            await interface.send_to(ctx)
                        else:
                            if result.strip() == '':
                                result = "\u200b"

                            await ctx.send(result.replace(self.bot.http.token, "[token omitted]"))

    @jsk.command(name="py_inspect", aliases=["pyi", "python_inspect", "pythoninspect"])
    async def jsk_python_inspect(self, ctx: commands.Context, *, argument: CodeblockConverter):
        """
        Evaluation of Python code with inspect information.
        """

        arg_dict = get_var_dict_from_ctx(ctx)

        scope = self.scope

        scope.clean()
        arg_dict["_"] = self.last_result

        async with ReplResponseReactor(ctx.message):
            with self.submit(ctx):
                async for result in AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict):
                    self.last_result = result

                    header = repr(result).replace("``", "`\u200b`").replace(self.bot.http.token, "[token omitted]")

                    if len(header) > 485:
                        header = header[0:482] + "..."

                    paginator = WrappedPaginator(prefix=f"```prolog\n=== {header} ===\n", max_size=1985)

                    for name, res in all_inspections(result):
                        paginator.add_line(f"{name:16.16} :: {res}")

                    interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                    await interface.send_to(ctx)

    @jsk.command(name="shell", aliases=["sh"])
    async def jsk_shell(self, ctx: commands.Context, *, argument: CodeblockConverter):
        """
        Executes statements in the system shell.

        This uses the bash shell. Execution can be cancelled by closing the paginator.
        """

        async with ReplResponseReactor(ctx.message):
            with self.submit(ctx):
                paginator = WrappedPaginator(prefix="```sh", max_size=1985)
                paginator.add_line(f"$ {argument.content}\n")

                interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                self.bot.loop.create_task(interface.send_to(ctx))

                with ShellReader(argument.content) as reader:
                    async for line in reader:
                        if interface.closed:
                            return
                        await interface.add_line(line)

                await interface.add_line(f"\n[status] Return code {reader.close_code}")

    @jsk.command(name="git")
    async def jsk_git(self, ctx: commands.Context, *, argument: CodeblockConverter):
        """
        Shortcut for 'jsk sh git'. Invokes the system shell.
        """

        return await ctx.invoke(self.jsk_shell, argument=Codeblock(argument.language, "git " + argument.content))

    @jsk.command(name="load", aliases=["reload"])
    async def jsk_load(self, ctx: commands.Context, *extensions):
        """
        Loads or reloads the given extension names.

        Reports any extensions that failed to load.
        """

        paginator = commands.Paginator(prefix='', suffix='')

        for extension in extensions:
            load_icon = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}" \
                        if extension in self.bot.extensions else "\N{INBOX TRAY}"
            try:
                self.bot.unload_extension(extension)
                self.bot.load_extension(extension)
            except Exception as exc:  # pylint: disable=broad-except
                traceback_data = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(f"\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```", empty=True)
            else:
                paginator.add_line(f"{load_icon} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.send(page)

    @jsk.command(name="unload")
    async def jsk_unload(self, ctx: commands.Context, *extensions):
        """
        Unloads the given extension names.

        Reports any extensions that failed to unload.
        """

        paginator = commands.Paginator(prefix='', suffix='')

        for extension in extensions:
            try:
                self.bot.unload_extension(extension)
            except Exception as exc:  # pylint: disable=broad-except
                traceback_data = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(f"\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```", empty=True)
            else:
                paginator.add_line(f"\N{OUTBOX TRAY} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.send(page)

    @jsk.group(name="voice", aliases=["vc"])
    @commands.check(vc_check)
    async def jsk_voice(self, ctx: commands.Context):
        """
        Voice-related commands.

        If invoked without subcommand, relays current voice state.
        """

        # if using a subcommand, short out
        if ctx.invoked_subcommand is not None and ctx.invoked_subcommand is not self.jsk_voice:
            return

        # give info about the current voice client if there is one
        voice = ctx.guild.voice_client

        if not voice or not voice.is_connected():
            return await ctx.send("Not connected.")

        await ctx.send(f"Connected to {voice.channel.name}, "
                       f"{'paused' if voice.is_paused() else 'playing' if voice.is_playing() else 'idle'}.")

    @jsk_voice.command(name="join", aliases=["connect"])
    async def jsk_vc_join(self, ctx: commands.Context, *,
                          destination: typing.Union[discord.VoiceChannel, discord.Member] = None):
        """
        Joins a voice channel, or moves to it if already connected.

        Passing a voice channel uses that voice channel.
        Passing a member will use that member's current voice channel.
        Passing nothing will use the author's voice channel.
        """

        destination = destination or ctx.author

        if isinstance(destination, discord.Member):
            if destination.voice and destination.voice.channel:
                destination = destination.voice.channel
            else:
                return await ctx.send("Member has no voice channel.")

        voice = ctx.guild.voice_client

        if voice:
            await voice.move_to(destination)
        else:
            await destination.connect(reconnect=True)

        await ctx.send(f"Connected to {destination.name}.")

    @jsk_voice.command(name="disconnect", aliases=["dc"])
    @commands.check(connected_check)
    async def jsk_vc_disconnect(self, ctx: commands.Context):
        """
        Disconnects from the voice channel in this guild, if there is one.
        """

        voice = ctx.guild.voice_client

        await voice.disconnect()
        await ctx.send(f"Disconnected from {voice.channel.name}.")

    @jsk_voice.command(name="stop")
    @commands.check(playing_check)
    async def jsk_vc_stop(self, ctx: commands.Context):
        """
        Stops running an audio source, if there is one.
        """

        voice = ctx.guild.voice_client

        voice.stop()
        await ctx.send(f"Stopped playing audio in {voice.channel.name}.")

    @jsk_voice.command(name="pause")
    @commands.check(playing_check)
    async def jsk_vc_pause(self, ctx: commands.Context):
        """
        Pauses a running audio source, if there is one.
        """

        voice = ctx.guild.voice_client

        if voice.is_paused():
            return await ctx.send("Audio is already paused.")

        voice.pause()
        await ctx.send(f"Paused audio in {voice.channel.name}.")

    @jsk_voice.command(name="resume")
    @commands.check(playing_check)
    async def jsk_vc_resume(self, ctx: commands.Context):
        """
        Resumes a running audio source, if there is one.
        """

        voice = ctx.guild.voice_client

        if not voice.is_paused():
            return await ctx.send("Audio is not paused.")

        voice.resume()
        await ctx.send(f"Resumed audio in {voice.channel.name}.")

    @jsk_voice.command(name="volume")
    @commands.check(playing_check)
    async def jsk_vc_volume(self, ctx: commands.Context, *, percentage: float):
        """
        Adjusts the volume of an audio source if it is supported.
        """

        volume = max(0.0, min(1.0, percentage / 100))

        source = ctx.guild.voice_client.source

        if not isinstance(source, discord.PCMVolumeTransformer):
            return await ctx.send("This source doesn't support adjusting volume or "
                                  "the interface to do so is not exposed.")

        source.volume = volume

        await ctx.send(f"Volume set to {volume * 100:.2f}%")

    @jsk_voice.command(name="play", aliases=["play_local"])
    @commands.check(connected_check)
    async def jsk_vc_play(self, ctx: commands.Context, *, uri: str):
        """
        Plays audio direct from a URI.

        Can be either a local file or an audio resource on the internet.
        """

        voice = ctx.guild.voice_client

        if voice.is_playing():
            voice.stop()

        # remove embed maskers if present
        uri = uri.lstrip("<").rstrip(">")

        voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(uri)))
        await ctx.send(f"Playing in {voice.channel.name}.")

    @jsk_voice.command(name="youtube_dl", aliases=["youtubedl", "ytdl", "yt"])
    @commands.check(connected_check)
    async def jsk_vc_youtube_dl(self, ctx: commands.Context, *, url: str):
        """
        Plays audio from youtube_dl-compatible sources.
        """

        if not youtube_dl:
            return await ctx.send("youtube_dl is not installed.")

        voice = ctx.guild.voice_client

        if voice.is_playing():
            voice.stop()

        # remove embed maskers if present
        url = url.lstrip("<").rstrip(">")

        voice.play(discord.PCMVolumeTransformer(BasicYouTubeDLSource(url)))
        await ctx.send(f"Playing in {voice.channel.name}.")

    @jsk.command(name="su")
    async def jsk_su(self, ctx: commands.Context, member: typing.Union[discord.Member, discord.User],
                     *, command_string: str):
        """
        Run a command as someone else.

        This will try to resolve to a Member, but will use a User if it can't find one.
        """

        alt_ctx = await copy_context_with(ctx, author=member, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        return await alt_ctx.command.invoke(alt_ctx)

    @jsk.command(name="sudo")
    async def jsk_sudo(self, ctx: commands.Context, *, command_string: str):
        """
        Run a command bypassing all checks and cooldowns.

        This also bypasses permission checks so this has a high possibility of making a command raise.
        """

        alt_ctx = await copy_context_with(ctx, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        return await alt_ctx.command.reinvoke(alt_ctx)

    @jsk.command(name="debug", aliases=["dbg"])
    async def jsk_debug(self, ctx: commands.Context, *, command_string: str):
        """
        Run a command timing execution and catching exceptions.
        """

        alt_ctx = await copy_context_with(ctx, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        start = time.perf_counter()

        async with ReplResponseReactor(ctx.message):
            with self.submit(ctx):
                await alt_ctx.command.invoke(alt_ctx)

        end = time.perf_counter()
        return await ctx.send(f"Command `{alt_ctx.command.qualified_name}` finished in {end - start:.3f}s.")

    @jsk.command(name="shutdown", aliases=["logout"])
    async def jsk_shutdown(self, ctx: commands.Context):
        """
        Logs this bot out.
        """

        await ctx.send("Logging out now..")
        await ctx.bot.logout()


def setup(bot: commands.Bot):
    """
    Adds the Jishaku cog to the bot.
    """

    bot.add_cog(Jishaku(bot=bot))
