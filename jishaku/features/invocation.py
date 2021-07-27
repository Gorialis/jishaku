# -*- coding: utf-8 -*-

"""
jishaku.features.invocation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The jishaku command invocation related commands.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import contextlib
import inspect
import io
import pathlib
import re
import time
import typing

import discord
from discord.ext import commands

from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.models import copy_context_with
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check

UserIDConverter = commands.IDConverter[discord.User] if discord.version_info >= (2, 0) else commands.IDConverter


class SlimUserConverter(UserIDConverter):  # pylint: disable=too-few-public-methods
    """
    Identical to the stock UserConverter, but does not perform plaintext name checks.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.User:
        """Converter method"""
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]{15,20})>$', argument)

        if match is not None:
            user_id = int(match.group(1))
            result = ctx.bot.get_user(user_id) or discord.utils.get(ctx.message.mentions, id=user_id)
            if result is None:
                try:
                    result = await ctx.bot.fetch_user(user_id)
                except discord.HTTPException:
                    raise commands.UserNotFound(argument) from None

            return result

        raise commands.UserNotFound(argument)


class InvocationFeature(Feature):
    """
    Feature containing the command invocation related commands
    """

    if hasattr(discord, 'Thread'):
        OVERRIDE_SIGNATURE = typing.Union[SlimUserConverter, discord.TextChannel, discord.Thread]  # pylint: disable=no-member
    else:
        OVERRIDE_SIGNATURE = typing.Union[SlimUserConverter, discord.TextChannel]

    @Feature.Command(parent="jsk", name="override", aliases=["execute", "exec", "override!", "execute!", "exec!"])
    async def jsk_override(
        self, ctx: commands.Context,
        overrides: commands.Greedy[OVERRIDE_SIGNATURE],
        *, command_string: str
    ):
        """
        Run a command with a different user, channel, or thread, optionally bypassing checks and cooldowns.

        Users will try to resolve to a Member, but will use a User if it can't find one.
        """

        kwargs = {
            "content": ctx.prefix + command_string.lstrip('/')
        }

        for override in overrides:
            if isinstance(override, discord.User):
                # This is a user
                if ctx.guild:
                    # Try to upgrade to a Member instance
                    # This used to be done by a Union converter, but doing it like this makes
                    #  the command more compatible with chaining, e.g. `jsk in .. jsk su ..`
                    target_member = None

                    with contextlib.suppress(discord.HTTPException):
                        target_member = ctx.guild.get_member(override.id) or await ctx.guild.fetch_member(override.id)

                    kwargs["author"] = target_member or override
                else:
                    kwargs["author"] = override
            else:
                # Otherwise, is a text channel or a thread
                kwargs["channel"] = override

        alt_ctx = await copy_context_with(ctx, **kwargs)

        if alt_ctx.command is None:
            if alt_ctx.invoked_with is None:
                return await ctx.send('This bot has been hard-configured to ignore this user.')
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        if ctx.invoked_with.endswith('!'):
            return await alt_ctx.command.reinvoke(alt_ctx)

        return await alt_ctx.command.invoke(alt_ctx)

    @Feature.Command(parent="jsk", name="repeat")
    async def jsk_repeat(self, ctx: commands.Context, times: int, *, command_string: str):
        """
        Runs a command multiple times in a row.

        This acts like the command was invoked several times manually, so it obeys cooldowns.
        You can use this in conjunction with `jsk sudo` to bypass this.
        """

        with self.submit(ctx):  # allow repeats to be cancelled
            for _ in range(times):
                alt_ctx = await copy_context_with(ctx, content=ctx.prefix + command_string)

                if alt_ctx.command is None:
                    return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

                await alt_ctx.command.reinvoke(alt_ctx)

    @Feature.Command(parent="jsk", name="debug", aliases=["dbg"])
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

    @Feature.Command(parent="jsk", name="source", aliases=["src"])
    async def jsk_source(self, ctx: commands.Context, *, command_name: str):
        """
        Displays the source code for a command.
        """

        command = self.bot.get_command(command_name)
        if not command:
            return await ctx.send(f"Couldn't find command `{command_name}`.")

        try:
            source_lines, _ = inspect.getsourcelines(command.callback)
        except (TypeError, OSError):
            return await ctx.send(f"Was unable to retrieve the source for `{command}` for some reason.")

        filename = "source.py"

        try:
            filename = pathlib.Path(inspect.getfile(command.callback)).name
        except (TypeError, OSError):
            pass

        # getsourcelines for some reason returns WITH line endings
        source_text = ''.join(source_lines)

        if use_file_check(ctx, len(source_text)):  # File "full content" preview limit
            await ctx.send(file=discord.File(
                filename=filename,
                fp=io.BytesIO(source_text.encode('utf-8'))
            ))
        else:
            paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1985)

            paginator.add_line(source_text.replace('```', '``\N{zero width space}`'))

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            await interface.send_to(ctx)
