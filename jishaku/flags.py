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

ENABLED_SYMBOLS = ("true", "t", "yes", "y", "on", "1")
DISABLED_SYMBOLS = ("false", "f", "no", "n", "off", "0")


@dataclasses.dataclass
class Flag:
    """
    Dataclass that represents a Jishaku flag state. Only for internal use.
    """

    name: str
    flag_type: type
    default: typing.Callable = None
    override: typing.Any = None

    def resolve(self, flags):  # pylint: disable=too-many-return-statements
        """
        Resolve this flag. Only for internal use.
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


class FlagMeta(type):
    """
    Metaclass for Flags.
    This handles the Just-In-Time evaluation of flags, allowing them to be overridden during execution.
    """

    def __new__(cls, name, base, attrs):
        attrs['flag_map'] = {}

        for flag_name, flag_type in attrs['__annotations__'].items():
            attrs['flag_map'][flag_name] = Flag(flag_name, flag_type, attrs.pop(flag_name, None))

        return super(FlagMeta, cls).__new__(cls, name, base, attrs)

    def __getattr__(cls, name: str):
        if hasattr(cls, 'flag_map') and name in cls.flag_map:
            return cls.flag_map[name].resolve(cls)

        return super().__getattribute__(name)

    def __setattr__(cls, name: str, value):
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
    SCOPE_PREFIX: str = lambda flags: '' if flags.NO_UNDERSCORE else '_'

    # Flag to indicate whether to always use paginators over relying on Discord's file preview
    FORCE_PAGINATOR: bool

    # Flag to indicate verbose error tracebacks should be sent to the invoking channel as opposed to via direct message.
    NO_DM_TRACEBACK: bool

    # Flag to indicate usage of braille J in shutdown command
    USE_BRAILLE_J: bool
