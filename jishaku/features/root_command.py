# -*- coding: utf-8 -*-

"""
jishaku.features.root_command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The jishaku root command.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import sys
import typing

import discord
import humanize
from discord.ext import commands

from jishaku.features.baseclass import Feature
from jishaku.flags import JISHAKU_HIDE
from jishaku.meta import __version__
from jishaku.modules import package_version
from jishaku.paginators import PaginatorInterface

try:
    import psutil
except ImportError:
    psutil = None


class RootCommand(Feature):
    """
    Feature containing the root jsk command
    """

    @Feature.Command(name="jishaku", aliases=["jsk"], hidden=JISHAKU_HIDE,
                     invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: commands.Context):
        """
        The Jishaku debug and diagnostic commands.

        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """

        summary = [
            f"Jishaku v{__version__}, discord.py `{package_version('discord.py')}`, "
            f"`Python {sys.version}` on `{sys.platform}`".replace("\n", ""),
            f"Module was loaded {humanize.naturaltime(self.load_time)}, "
            f"cog was loaded {humanize.naturaltime(self.start_time)}.",
            ""
        ]

        # detect if [procinfo] feature is installed
        if psutil:
            try:
                proc = psutil.Process()

                with proc.oneshot():
                    try:
                        mem = proc.memory_full_info()
                        summary.append(f"Using {humanize.naturalsize(mem.rss)} physical memory and "
                                       f"{humanize.naturalsize(mem.vms)} virtual memory, "
                                       f"{humanize.naturalsize(mem.uss)} of which unique to this process.")
                    except psutil.AccessDenied:
                        pass

                    try:
                        name = proc.name()
                        pid = proc.pid
                        thread_count = proc.num_threads()

                        summary.append(f"Running on PID {pid} (`{name}`) with {thread_count} thread(s).")
                    except psutil.AccessDenied:
                        pass

                    summary.append("")  # blank line
            except psutil.AccessDenied:
                summary.append(
                    "psutil is installed, but this process does not have high enough access rights "
                    "to query process information."
                )
                summary.append("")  # blank line

        cache_summary = f"{len(self.bot.guilds)} guild(s) and {len(self.bot.users)} user(s)"

        # Show shard settings to summary
        if isinstance(self.bot, discord.AutoShardedClient):
            summary.append(f"This bot is automatically sharded and can see {cache_summary}.")
        elif self.bot.shard_count:
            summary.append(f"This bot is manually sharded and can see {cache_summary}.")
        else:
            summary.append(f"This bot is not sharded and can see {cache_summary}.")

        # pylint: disable=protected-access
        if self.bot._connection.max_messages:
            message_cache = f"Message cache capped at {self.bot._connection.max_messages}"
        else:
            message_cache = "Message cache is disabled"

        if discord.version_info >= (1, 5, 0):
            presence_intent = f"presence intent is {'enabled' if self.bot.intents.presences else 'disabled'}"
            members_intent = f"members intent is {'enabled' if self.bot.intents.members else 'disabled'}"

            summary.append(f"{message_cache}, {presence_intent} and {members_intent}.")
        else:
            guild_subscriptions = f"guild subscriptions are {'enabled' if self.bot._connection.guild_subscriptions else 'disabled'}"

            summary.append(f"{message_cache} and {guild_subscriptions}.")

        # pylint: enable=protected-access

        # Show websocket latency in milliseconds
        summary.append(f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms")

        await ctx.send("\n".join(summary))

    # pylint: disable=no-member
    @Feature.Command(parent="jsk", name="hide")
    async def jsk_hide(self, ctx: commands.Context):
        """
        Hides Jishaku from the help command.
        """

        if self.jsk.hidden:
            return await ctx.send("Jishaku is already hidden.")

        self.jsk.hidden = True
        await ctx.send("Jishaku is now hidden.")

    @Feature.Command(parent="jsk", name="show")
    async def jsk_show(self, ctx: commands.Context):
        """
        Shows Jishaku in the help command.
        """

        if not self.jsk.hidden:
            return await ctx.send("Jishaku is already visible.")

        self.jsk.hidden = False
        await ctx.send("Jishaku is now visible.")
    # pylint: enable=no-member

    @Feature.Command(parent="jsk", name="tasks")
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
        return await interface.send_to(ctx)

    @Feature.Command(parent="jsk", name="cancel")
    async def jsk_cancel(self, ctx: commands.Context, *, index: typing.Union[int, str]):
        """
        Cancels a task with the given index.

        If the index passed is -1, will cancel the last task instead.
        """

        if not self.tasks:
            return await ctx.send("No tasks to cancel.")

        if index == "~":
            task_count = len(self.tasks)

            for task in self.tasks:
                task.task.cancel()

            self.tasks.clear()

            return await ctx.send(f"Cancelled {task_count} tasks.")

        if isinstance(index, str):
            raise commands.BadArgument('Literal for "index" not recognized.')

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
