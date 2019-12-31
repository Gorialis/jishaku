# -*- coding: utf-8 -*-

"""
jishaku.flags
~~~~~~~~~~~~~~

The Jishaku cog base, which contains most of the actual functionality of Jishaku.

:copyright: (c) 2020 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import os

ENABLED_SYMBOLS = ("true", "t", "yes", "y", "on", "1")


def enabled(flag: str) -> bool:
    """
    Returns whether an environment flag is enabled.
    """

    return os.getenv(flag, "").lower() in ENABLED_SYMBOLS


# Flag to indicate the Jishaku base command group should be hidden
JISHAKU_HIDE = enabled("JISHAKU_HIDE")

# Flag to indicate that retention mode for REPL should be enabled by default
JISHAKU_RETAIN = enabled("JISHAKU_RETAIN")

# Flag to indicate that meta variables in REPL should not be prefixed with an underscore
JISHAKU_NO_UNDERSCORE = enabled("JISHAKU_NO_UNDERSCORE")
SCOPE_PREFIX = '' if JISHAKU_NO_UNDERSCORE else '_'

# Flag to indicate verbose error tracebacks should be sent to the invoking channel as opposed to via direct message.
JISHAKU_NO_DM_TRACEBACK = enabled("JISHAKU_NO_DM_TRACEBACK")
