# -*- coding: utf-8 -*-

"""
jishaku.features.baseclass
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The base Feature class that serves as the superclass of all feature components.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import collections
import contextlib
import sys
import typing
from datetime import datetime, timezone

import discord
from discord.ext import commands

from jishaku.types import BotT, ContextA

__all__ = (
    'Feature',
    'CommandTask'
)


if typing.TYPE_CHECKING or discord.version_info >= (2, 0, 0):
    _ConvertedCommand = commands.Command['Feature', typing.Any, typing.Any]
    _ConvertedGroup = commands.Group['Feature', typing.Any, typing.Any]
else:
    _ConvertedCommand = commands.Command
    _ConvertedGroup = commands.Group


_FeatureCommandToCommand = typing.Callable[
    ...,
    typing.Callable[
        [typing.Callable[..., typing.Any]],
        _ConvertedCommand
    ]
]
_FeatureCommandToGroup = typing.Callable[
    ...,
    typing.Callable[
        [typing.Callable[..., typing.Any]],
        _ConvertedGroup
    ]
]

T = typing.TypeVar('T')

if sys.version_info < (3, 10):
    from typing_extensions import Concatenate, ParamSpec
    P = ParamSpec('P')
    Task = asyncio.Task
else:
    Concatenate = typing.Concatenate  # pylint: disable=no-member
    P = typing.ParamSpec('P')  # pylint: disable=no-member
    Task = asyncio.Task[typing.Any]

GenericFeature = typing.TypeVar('GenericFeature', bound='Feature')


class CommandTask(typing.NamedTuple):
    """
    A running Jishaku task, wrapping asyncio.Task
    """

    index: int  # type: ignore
    ctx: ContextA
    task: typing.Optional[Task]


class Feature(commands.Cog):
    """
    Baseclass defining feature components of the jishaku cog.
    """

    class Command(typing.Generic[GenericFeature, P, T]):  # pylint: disable=too-few-public-methods
        """
        An intermediary class for Feature commands.
        Instances of this class will be converted into commands.Command or commands.Group instances when inside a Feature.

        :param parent: What this command should be parented to.
        :param standalone_ok: Whether the command should be allowed to be standalone if its parent isn't found.
        """

        def __init__(
            self,
            parent: typing.Optional[str] = None,
            standalone_ok: bool = False,
            **kwargs: typing.Any
        ):
            self.parent: typing.Optional[str] = parent
            self.parent_instance: typing.Optional[Feature.Command[GenericFeature, typing.Any, typing.Any]] = None
            self.standalone_ok = standalone_ok
            self.kwargs = kwargs
            self.callback: typing.Optional[
                typing.Callable[
                    Concatenate[GenericFeature, ContextA, P],
                    typing.Coroutine[typing.Any, typing.Any, T]
                ]
            ] = None
            self.depth: int = 0
            self.has_children: bool = False

        def __call__(
            self,
            callback: typing.Callable[
                ...,
                # This causes a weird pyright bug right now
                # Concatenate[GenericFeature, ContextA, P],
                typing.Coroutine[typing.Any, typing.Any, T]
            ]
        ):
            self.callback = callback  # type: ignore
            return self

        def convert(
            self,
            association_map: typing.Dict[
                'Feature.Command[GenericFeature, typing.Any, typing.Any]',
                'commands.Command[GenericFeature, typing.Any, typing.Any]',
            ]
        ) -> 'commands.Command[GenericFeature, P, T]':
            """
            Attempts to convert this Feature.Command into either a commands.Command or commands.Group
            """

            if self.parent:
                if not self.parent_instance:
                    raise RuntimeError("A Features.Command declared as having a parent was attempted to be converted before its parent was")

                parent = association_map[self.parent_instance]

                if not isinstance(parent, commands.Group):
                    raise RuntimeError("A Features.Command declared as a parent was associated with a non-commands.Group")

                command_type = parent.group if self.has_children else parent.command
            else:
                command_type = commands.group if self.has_children else commands.command

            if not self.callback:
                raise RuntimeError("A Features.Command lacked a callback at the time it was attempted to be converted")

            return command_type(**self.kwargs)(self.callback)

    load_time: datetime = datetime.utcnow().replace(tzinfo=timezone.utc)

    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        self.bot: BotT = kwargs.pop('bot')
        self.start_time: datetime = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.tasks: typing.Deque[CommandTask] = collections.deque()
        self.task_count: int = 0

        # Generate and attach commands
        command_lookup: typing.Dict[str, Feature.Command['Feature', typing.Any, typing.Any]] = {}

        for kls in reversed(type(self).__mro__):
            for key, cmd in kls.__dict__.items():
                if isinstance(cmd, Feature.Command):
                    command_lookup[key] = cmd  # type: ignore

        command_set = list(command_lookup.items())

        # Try to associate every parented command with its parent
        for key, cmd in command_set:
            cmd.parent_instance = None
            cmd.depth = 0

            if cmd.parent and isinstance(cmd.parent, str):  # type: ignore
                if cmd.standalone_ok:
                    cmd.parent_instance = command_lookup.get(cmd.parent, None)
                else:
                    try:
                        cmd.parent_instance = command_lookup[cmd.parent]
                    except KeyError as exception:
                        raise RuntimeError(
                            f"Couldn't associate feature command {key} with its parent {cmd.parent}"
                        ) from exception
            # Also raise if any command lacks a callback
            if cmd.callback is None:
                raise RuntimeError(f"Feature command {key} lacks callback")

        # Assign depth and has_children
        for key, cmd in command_set:
            parent = cmd.parent_instance
            # Recurse parents increasing depth until we reach the top
            while parent:
                parent.has_children = True
                cmd.depth += 1
                parent = parent.parent_instance

        # Sort by depth
        command_set.sort(key=lambda c: c[1].depth)
        association_map: typing.Dict[
            Feature.Command['Feature', typing.Any, typing.Any],
            commands.Command['Feature', typing.Any, typing.Any]
        ] = {}

        self.feature_commands: typing.Dict[
            str,
            commands.Command['Feature', typing.Any, typing.Any]
        ] = {}

        for key, cmd in command_set:
            association_map[cmd] = target_cmd = cmd.convert(association_map)
            target_cmd.cog = self
            self.feature_commands[key] = target_cmd
            setattr(self, key, target_cmd)

        # pylint: disable=protected-access, access-member-before-definition
        self.__cog_commands__ = [*self.__cog_commands__, *self.feature_commands.values()]
        # pylint: enable=protected-access, access-member-before-definition

        # Don't really think this does much, but init Cog anyway.
        super().__init__(*args, **kwargs)

    # Ignored because this gets incorrectly clocked as a sync override
    async def cog_check(self, ctx: ContextA):  # type: ignore  # pylint: disable=invalid-overridden-method
        """
        Local check, makes all commands in resulting cogs owner-only
        """

        if not await ctx.bot.is_owner(ctx.author):
            raise commands.NotOwner("You must own this bot to use Jishaku.")
        return True

    @contextlib.contextmanager
    def submit(self, ctx: ContextA):
        """
        A context-manager that submits the current task to jishaku's task list
        and removes it afterwards.

        Parameters
        -----------
        ctx: commands.Context
            A Context object used to derive information about this command task.
        """

        self.task_count += 1

        try:
            current_task = asyncio.current_task()  # pylint: disable=no-member
        except RuntimeError:
            # asyncio.current_task doesn't document that it can raise RuntimeError, but it does.
            # It propagates from asyncio.get_running_loop(), so it happens when there is no loop running.
            # It's unclear if this is a regression or an intentional change, since in 3.6,
            #  asyncio.Task.current_task() would have just returned None in this case.
            current_task = None

        cmdtask = CommandTask(self.task_count, ctx, current_task)

        self.tasks.append(cmdtask)

        try:
            yield cmdtask
        finally:
            if cmdtask in self.tasks:
                self.tasks.remove(cmdtask)
