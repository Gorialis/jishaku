# -*- coding: utf-8 -*-

"""
jishaku.metacog
~~~~~~~~~~~~~~~

The metaclass definitions for the Jishaku cog.

:copyright: (c) 2020 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

from discord.ext import commands


class GroupCogMeta(commands.CogMeta):
    """
    A CogMeta metaclass that sets all unparented (non-nested) Commands under it as children
    of a global Group.

    This allows Jishaku to place all of its commands under a group, while maintaining the ability
    to override individual subcommands in subclasses.

    The Group will be inserted as an attribute of the resulting Cog under its function name.
    """

    def __new__(cls, *args, **kwargs):
        group = kwargs.pop('command_parent')

        new_cls = super().__new__(cls, *args, **kwargs)

        for subcommand in new_cls.__cog_commands__:
            if subcommand.parent is None:
                subcommand.parent = group
                subcommand.__original_kwargs__['parent'] = group

        new_cls.__cog_commands__.append(group)
        setattr(new_cls, group.callback.__name__, group)

        return new_cls
