# -*- coding: utf-8 -*-

"""
jishaku.flags
~~~~~~~~~~~~~~

The Jishaku cog base, which contains most of the actual functionality of Jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import dataclasses
import inspect
import os
import typing

import discord

from jishaku.types import ContextA

ENABLED_SYMBOLS = ("true", "t", "yes", "y", "on", "1")
DISABLED_SYMBOLS = ("false", "f", "no", "n", "off", "0")


FlagHandler = typing.Optional[typing.Callable[['FlagMeta'], typing.Any]]


@dataclasses.dataclass
class Flag:
    """
    Dataclass that represents a Jishaku flag state. Only for internal use.
    """

    name: str
    flag_type: type
    default: FlagHandler = None
    handler: FlagHandler = None
    override: typing.Any = None

    def resolve_raw(self, flags: 'FlagMeta'):  # pylint: disable=too-many-return-statements
        """
        Receive the intrinsic value for this flag, before optionally being processed by the handler.
        """

        # Manual override, ignore environment in this case
        if self.override is not None:
            return self.override

        # Resolve from environment
        env_value = os.getenv(f"JISHAKU_{self.name}", "").strip()

        if env_value:
            if self.flag_type is bool:
                if env_value.lower() in ENABLED_SYMBOLS:
                    return True
                if env_value.lower() in DISABLED_SYMBOLS:
                    return False
            else:
                return self.flag_type(env_value)

        # Fallback if no resolvation from environment
        if self.default is not None:
            if inspect.isfunction(self.default):
                return self.default(flags)

            return self.default

        return self.flag_type()

    def resolve(self, flags: 'FlagMeta'):
        """
        Resolve this flag. Only for internal use.
        Applies the handler when there is one.
        """

        value = self.resolve_raw(flags)

        if self.handler:
            return self.handler(value)  # type: ignore

        return value


class FlagMeta(type):
    """
    Metaclass for Flags.
    This handles the Just-In-Time evaluation of flags, allowing them to be overridden during execution.
    """

    def __new__(
        cls,
        name: str,
        base: typing.Tuple[typing.Type[typing.Any]],
        attrs: typing.Dict[str, typing.Any]
    ):
        attrs['flag_map'] = {}

        for flag_name, flag_type in attrs['__annotations__'].items():
            default: typing.Union[
                FlagHandler,
                typing.Tuple[
                    FlagHandler,  # default
                    FlagHandler,  # handler
                ],
            ] = attrs.pop(flag_name, None)
            handler: FlagHandler = None

            if isinstance(default, tuple):
                default, handler = default

            attrs['flag_map'][flag_name] = Flag(flag_name, flag_type, default, handler)

        return super(FlagMeta, cls).__new__(cls, name, base, attrs)

    def __getattr__(cls, name: str):
        cls.flag_map: typing.Dict[str, Flag]

        if hasattr(cls, 'flag_map') and name in cls.flag_map:
            return cls.flag_map[name].resolve(cls)

        return super().__getattribute__(name)

    def __setattr__(cls, name: str, value: typing.Any):
        if name in cls.flag_map:
            flag = cls.flag_map[name]

            if not isinstance(value, flag.flag_type):
                raise ValueError(f"Attempted to set flag {name} to type {type(value).__name__} (should be {flag.flag_type.__name__})")

            flag.override = value
        else:
            super().__setattr__(name, value)


class Flags(metaclass=FlagMeta):  # pylint: disable=too-few-public-methods
    """
    The flags for Jishaku.

    You can override these either through your environment, e.g.:
        export JISHAKU_HIDE=1
    Or you can override them programmatically:
        jishaku.Flags.HIDE = True
    """

    # Flag to indicate the Jishaku base command group should be hidden
    HIDE: bool

    # Flag to indicate that retention mode for REPL should be enabled by default
    RETAIN: bool

    # Flag to indicate that meta variables in REPL should not be prefixed with an underscore
    NO_UNDERSCORE: bool

    # The scope prefix, i.e. the prefix that appears before Jishaku's builtin variables in REPL sessions.
    # It is recommended that you set this programatically.
    SCOPE_PREFIX: str = lambda flags: '' if flags.NO_UNDERSCORE else '_'  # type: ignore

    # Flag to indicate whether to always use paginators over relying on Discord's file preview
    FORCE_PAGINATOR: bool

    # Flag to indicate verbose error tracebacks should be sent to the invoking channel as opposed to via direct message.
    # ALWAYS_DM_TRACEBACK takes precedence over this
    NO_DM_TRACEBACK: bool

    # Flag to indicate all errors, even minor ones like SyntaxErrors, should be sent via direct message.
    ALWAYS_DM_TRACEBACK: bool

    @classmethod
    def traceback_destination(cls, message: discord.Message) -> typing.Optional[discord.abc.Messageable]:
        """
        Determine what 'default' location to send tracebacks to
        When None, the caller should decide
        """

        if cls.ALWAYS_DM_TRACEBACK:
            return message.author

        if cls.NO_DM_TRACEBACK:
            return message.channel

        # Otherwise let the caller decide
        return None

    # Flag to indicate usage of braille J in shutdown command
    USE_BRAILLE_J: bool

    # Flag to indicate whether ANSI support should always be enabled
    # USE_ANSI_NEVER takes precedence over this
    USE_ANSI_ALWAYS: bool

    # Flag to indicate whether ANSI support should always be disabled
    USE_ANSI_NEVER: bool

    @classmethod
    def use_ansi(cls, ctx: ContextA) -> bool:
        """
        Determine whether to use ANSI support from flags and context
        """

        if cls.USE_ANSI_NEVER:
            return False

        if cls.USE_ANSI_ALWAYS:
            return True

        return not ctx.author.is_on_mobile() if isinstance(ctx.author, discord.Member) and ctx.bot.intents.presences else True
