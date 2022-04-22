# -*- coding: utf-8 -*-

"""
jishaku.features.management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The jishaku extension and bot control commands.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import itertools
import math
import re
import time
import traceback
import typing
from urllib.parse import urlencode

import discord
from discord.ext import commands

from jishaku.features.baseclass import Feature
from jishaku.flags import Flags
from jishaku.modules import ExtensionConverter
from jishaku.repl import inspections


class ManagementFeature(Feature):
    """
    Feature containing the extension and bot control commands
    """

    @Feature.Command(parent="jsk", name="load", aliases=["reload"])
    async def jsk_load(self, ctx: commands.Context, *extensions: ExtensionConverter):
        """
        Loads or reloads the given extension names.

        Reports any extensions that failed to load.
        """

        paginator = commands.Paginator(prefix='', suffix='')

        # 'jsk reload' on its own just reloads jishaku
        if ctx.invoked_with == 'reload' and not extensions:
            extensions = [['jishaku']]

        for extension in itertools.chain(*extensions):
            method, icon = (
                (self.bot.reload_extension, "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
                if extension in self.bot.extensions else
                (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                await discord.utils.maybe_coroutine(method, extension)
            except Exception as exc:  # pylint: disable=broad-except
                traceback_data = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                    empty=True
                )
            else:
                paginator.add_line(f"{icon} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.send(page)

    @Feature.Command(parent="jsk", name="unload")
    async def jsk_unload(self, ctx: commands.Context, *extensions: ExtensionConverter):
        """
        Unloads the given extension names.

        Reports any extensions that failed to unload.
        """

        paginator = commands.Paginator(prefix='', suffix='')
        icon = "\N{OUTBOX TRAY}"

        for extension in itertools.chain(*extensions):
            try:
                await discord.utils.maybe_coroutine(self.bot.unload_extension, extension)
            except Exception as exc:  # pylint: disable=broad-except
                traceback_data = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                    empty=True
                )
            else:
                paginator.add_line(f"{icon} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.send(page)

    @Feature.Command(parent="jsk", name="shutdown", aliases=["logout"])
    async def jsk_shutdown(self, ctx: commands.Context):
        """
        Logs this bot out.
        """

        ellipse_character = "\N{BRAILLE PATTERN DOTS-356}" if Flags.USE_BRAILLE_J else "\N{HORIZONTAL ELLIPSIS}"

        await ctx.send(f"Logging out now{ellipse_character}")
        await ctx.bot.close()

    @Feature.Command(parent="jsk", name="invite")
    async def jsk_invite(self, ctx: commands.Context, *perms: str):
        """
        Retrieve the invite URL for this bot.

        If the names of permissions are provided, they are requested as part of the invite.
        """

        scopes = ('bot', 'applications.commands')
        permissions = discord.Permissions()

        for perm in perms:
            if perm not in dict(permissions):
                raise commands.BadArgument(f"Invalid permission: {perm}")

            setattr(permissions, perm, True)

        application_info = await self.bot.application_info()

        query = {
            "client_id": application_info.id,
            "scope": "+".join(scopes),
            "permissions": permissions.value
        }

        return await ctx.send(
            f"Link to invite this bot:\n<https://discordapp.com/oauth2/authorize?{urlencode(query, safe='+')}>"
        )

    @Feature.Command(parent="jsk", name="rtt", aliases=["ping"])
    async def jsk_rtt(self, ctx: commands.Context):
        """
        Calculates Round-Trip Time to the API.
        """

        message = None

        # We'll show each of these readings as well as an average and standard deviation.
        api_readings = []
        # We'll also record websocket readings, but we'll only provide the average.
        websocket_readings = []

        # We do 6 iterations here.
        # This gives us 5 visible readings, because a request can't include the stats for itself.
        for _ in range(6):
            # First generate the text
            text = "Calculating round-trip time...\n\n"
            text += "\n".join(f"Reading {index + 1}: {reading * 1000:.2f}ms" for index, reading in enumerate(api_readings))

            if api_readings:
                average = sum(api_readings) / len(api_readings)

                if len(api_readings) > 1:
                    stddev = math.sqrt(sum(math.pow(reading - average, 2) for reading in api_readings) / (len(api_readings) - 1))
                else:
                    stddev = 0.0

                text += f"\n\nAverage: {average * 1000:.2f} \N{PLUS-MINUS SIGN} {stddev * 1000:.2f}ms"
            else:
                text += "\n\nNo readings yet."

            if websocket_readings:
                average = sum(websocket_readings) / len(websocket_readings)

                text += f"\nWebsocket latency: {average * 1000:.2f}ms"
            else:
                text += f"\nWebsocket latency: {self.bot.latency * 1000:.2f}ms"

            # Now do the actual request and reading
            if message:
                before = time.perf_counter()
                await message.edit(content=text)
                after = time.perf_counter()

                api_readings.append(after - before)
            else:
                before = time.perf_counter()
                message = await ctx.send(content=text)
                after = time.perf_counter()

                api_readings.append(after - before)

            # Ignore websocket latencies that are 0 or negative because they usually mean we've got bad heartbeats
            if self.bot.latency > 0.0:
                websocket_readings.append(self.bot.latency)

    SLASH_COMMAND_ERROR = re.compile(r"In ((?:\d+\.[a-z]+\.?)+)")

    @Feature.Command(parent="jsk", name="sync")
    async def jsk_sync(self, ctx: commands.Context, *targets: str):
        """
        Sync global or guild application commands to Discord.
        """

        paginator = commands.Paginator(prefix='', suffix='')

        guilds = set()
        for target in targets:
            if target == '$':
                guilds.add(None)
            elif target == '*':
                guilds |= set(self.bot.tree._guild_commands.keys())  # pylint: disable=protected-access
            elif target == '.':
                guilds.add(ctx.guild.id)
            else:
                try:
                    guilds.add(int(target))
                except ValueError as error:
                    raise commands.BadArgument(f"{target} is not a valid guild ID") from error

        if not guilds:
            guilds.add(None)

        guilds: typing.List[typing.Optional[int]] = list(guilds)
        guilds.sort(key=lambda g: (g is not None, g))

        for guild in guilds:
            slash_commands = self.bot.tree._get_all_commands(  # pylint: disable=protected-access
                guild=discord.Object(guild) if guild else None
            )
            payload = [command.to_dict() for command in slash_commands]

            try:
                if guild is None:
                    data = await self.bot.http.bulk_upsert_global_commands(self.bot.application_id, payload=payload)
                else:
                    data = await self.bot.http.bulk_upsert_guild_commands(self.bot.application_id, guild, payload=payload)

                synced = [discord.app_commands.AppCommand(data=d, state=ctx._state) for d in data]  # pylint: disable=protected-access

            except discord.HTTPException as error:
                # It's diagnosis time
                error_text = []
                for line in str(error).split("\n"):
                    error_text.append(line)

                    try:
                        match = self.SLASH_COMMAND_ERROR.match(line)
                        if not match:
                            continue

                        pool = slash_commands
                        selected_command = None
                        name = ""
                        parts = match.group(1).split('.')
                        assert len(parts) % 2 == 0

                        for part_index in range(0, len(parts), 2):
                            index = int(parts[part_index])
                            # prop = parts[part_index + 1]

                            if pool:
                                # If the pool exists, this should be a subcommand
                                selected_command = pool[index]
                                name += selected_command.name + " "

                                if hasattr(selected_command, '_children'):
                                    pool = list(selected_command._children.values())  # pylint: disable=protected-access
                                else:
                                    pool = None
                            else:
                                # Otherwise, the pool has been exhausted, and this likely is referring to a parameter
                                param = list(selected_command._params.keys())[index]  # pylint: disable=protected-access
                                name += f"(parameter: {param}) "

                        if selected_command:
                            to_inspect = None

                            if hasattr(selected_command, 'callback'):
                                to_inspect = selected_command.callback
                            elif isinstance(selected_command, commands.Cog):
                                to_inspect = type(selected_command)

                            try:
                                error_text.append(''.join([
                                    "\N{MAGNET} This is likely caused by: `",
                                    name,
                                    "` at ",
                                    str(inspections.file_loc_inspection(to_inspect)),
                                    ":",
                                    str(inspections.line_span_inspection(to_inspect))
                                ]))
                            except Exception:  # pylint: disable=broad-except
                                error_text.append(f"\N{MAGNET} This is likely caused by: `{name}`")

                    except Exception as error:  # pylint: disable=broad-except
                        error_text.append(f"\N{MAGNET} Couldn't determine cause: {type(error).__name__}: {error}")

                error_text = '\n'.join(error_text)

                if guild:
                    paginator.add_line(f"\N{WARNING SIGN} `{guild}`: {error_text}", empty=True)
                else:
                    paginator.add_line(f"\N{WARNING SIGN} Global: {error_text}", empty=True)
            else:
                if guild:
                    paginator.add_line(f"\N{SATELLITE ANTENNA} `{guild}` Synced {len(synced)} guild commands", empty=True)
                else:
                    paginator.add_line(f"\N{SATELLITE ANTENNA} Synced {len(synced)} global commands", empty=True)

        for page in paginator.pages:
            await ctx.send(page)
