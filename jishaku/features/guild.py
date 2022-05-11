# -*- coding: utf-8 -*-

"""
jishaku.features.guild
~~~~~~~~~~~~~~~~~~~~~~~~

The jishaku guild-related commands.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import typing

import discord

from jishaku.features.baseclass import Feature
from jishaku.types import ContextA

T = typing.TypeVar('T')


class GuildFeature(Feature):
    """
    Feature containing the guild-related commands
    """

    @staticmethod
    def apply_overwrites(
        permissions: typing.Dict[str, typing.Tuple[bool, str]],
        allow: int,
        deny: int,
        name: str
    ):
        """
        Applies overwrites to the permissions dictionary (see permtrace),
        based on an allow and deny mask.
        """

        allow_p: discord.Permissions = discord.Permissions(allow)
        deny_p: discord.Permissions = discord.Permissions(deny)

        # Denies first..
        for key, value in dict(deny_p).items():
            # Check that this is denied and it is not already denied
            # (we want to show the lowest-level reason for the denial)
            if value and permissions[key][0]:
                permissions[key] = (False, f"it is the channel's {name} overwrite")

        # Then allows
        for key, value in dict(allow_p).items():
            # Check that this is allowed and it is not already allowed
            # (we want to show the lowest-level reason for the allowance)
            if value and not permissions[key][0]:
                permissions[key] = (True, f"it is the channel's {name} overwrite")

    @staticmethod
    def chunks(array: typing.List[T], chunk_size: int) -> typing.Generator[typing.List[T], None, None]:
        """
        Chunks a list into chunks of a given size.
        Should probably be in utils, honestly.
        """
        for i in range(0, len(array), chunk_size):
            yield array[i:i + chunk_size]

    @Feature.Command(parent="jsk", name="permtrace")
    async def jsk_permtrace(
        self,
        ctx: ContextA,
        channel: typing.Union[discord.TextChannel, discord.VoiceChannel],
        *targets: typing.Union[discord.Member, discord.Role]
    ):
        """
        Calculates the source of granted or rejected permissions.

        This accepts a channel, and either a member or a list of roles.
        It calculates permissions the same way Discord does, while keeping track of the source.
        """

        member_ids = {target.id: target for target in targets if isinstance(target, discord.Member)}
        roles: typing.List[discord.Role] = []

        for target in targets:
            if isinstance(target, discord.Member):
                roles.extend(list(target.roles))
            else:
                roles.append(target)

        # Remove duplicates
        roles = list(set(roles))

        # Dictionary to store the current permission state and reason
        # Stores <perm name>: (<perm allowed>, <reason>)
        permissions: typing.Dict[str, typing.Tuple[bool, str]] = {}

        if member_ids and channel.guild.owner_id in member_ids:
            # Is owner, has all perms
            for key in dict(discord.Permissions.all()).keys():
                permissions[key] = (True, f"<@{channel.guild.owner_id}> owns the server")
        else:
            # Otherwise, either not a member or not the guild owner, calculate perms manually
            is_administrator = False

            # Handle guild-level perms first
            for key, value in dict(channel.guild.default_role.permissions).items():
                permissions[key] = (value, "it is the server-wide @everyone permission")

            for role in roles:
                for key, value in dict(role.permissions).items():
                    # Roles can only ever allow permissions
                    # Denying a permission does nothing if a lower role allows it
                    if value and not permissions[key][0]:
                        permissions[key] = (value, f"it is the server-wide {role.name} permission")

                # Then administrator handling
                if role.permissions.administrator:
                    is_administrator = True

                    for key in dict(discord.Permissions.all()).keys():
                        if not permissions[key][0]:
                            permissions[key] = (True, f"it is granted by Administrator on the server-wide {role.name} permission")

            # If Administrator was granted, there is no reason to even do channel permissions
            if not is_administrator:
                # Now channel-level permissions

                # Special case for @everyone
                # pylint: disable=protected-access
                try:
                    maybe_everyone = channel._overwrites[0]  # type: ignore
                    if maybe_everyone.id == channel.guild.default_role.id:
                        self.apply_overwrites(permissions, allow=maybe_everyone.allow, deny=maybe_everyone.deny, name="@everyone")
                        remaining_overwrites = channel._overwrites[1:]  # type: ignore
                    else:
                        remaining_overwrites = channel._overwrites  # type: ignore
                except IndexError:
                    remaining_overwrites = channel._overwrites  # type: ignore
                # pylint: enable=protected-access

                role_lookup = {r.id: r for r in roles}

                def is_role(overwrite: discord.abc._Overwrites) -> bool:  # type: ignore
                    if discord.version_info >= (2, 0, 0):
                        return overwrite.is_role()
                    return overwrite.type == 'role'  # type: ignore

                def is_member(overwrite: discord.abc._Overwrites) -> bool:  # type: ignore
                    if discord.version_info >= (2, 0, 0):
                        return overwrite.is_member()
                    return overwrite.type == 'member'  # type: ignore

                # Denies are applied BEFORE allows, always
                # Handle denies
                for overwrite in remaining_overwrites:
                    if is_role(overwrite) and overwrite.id in role_lookup:
                        self.apply_overwrites(permissions, allow=0, deny=overwrite.deny, name=role_lookup[overwrite.id].name)

                # Handle allows
                for overwrite in remaining_overwrites:
                    if is_role(overwrite) and overwrite.id in role_lookup:
                        self.apply_overwrites(permissions, allow=overwrite.allow, deny=0, name=role_lookup[overwrite.id].name)

                if member_ids:
                    # Handle member-specific overwrites
                    for overwrite in remaining_overwrites:
                        if is_member(overwrite) and overwrite.id in member_ids:
                            self.apply_overwrites(permissions, allow=overwrite.allow, deny=overwrite.deny, name=f"{member_ids[overwrite.id].mention}")
                            break

        # Construct embed
        description = f"This is the permissions calculation for the following targets in {channel.mention}:\n"
        description += "\n".join(f"- {target.mention}" for target in targets)

        description += (
            "\nPlease note the reasons shown are the **most fundamental** reason why a permission is as it is. "
            "There may be other reasons that persist these permissions even if you change the things displayed."
        )

        embed = discord.Embed(color=0x00FF00, description=description)

        allows: typing.List[str] = []
        denies: typing.List[str] = []

        for key, value in permissions.items():
            if value[0]:
                allows.append(f"\N{WHITE HEAVY CHECK MARK} {key} (because {value[1]})")
            else:
                denies.append(f"\N{CROSS MARK} {key} (because {value[1]})")

        for chunk in self.chunks(sorted(allows) + sorted(denies), 8):
            embed.add_field(name="...", value="\n".join(chunk), inline=False)

        await ctx.send(embed=embed)
