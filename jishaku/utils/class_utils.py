# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2017 Devon R

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import discord
import subprocess
import typing

from .async_utils import *


__all__ = ("ReactionProcedureTimer", "ReplResponseReactor")


class ReactionProcedureTimer:
    """
    Class that reacts to a message based on what happens during its lifetime.
    """
    __slots__ = ('message', 'loop', 'handle', 'raised')

    def __init__(self, message: discord.Message, loop: typing.Optional[asyncio.BaseEventLoop] = None):
        self.message = message
        self.loop = loop or asyncio.get_event_loop()
        self.handle = None
        self.raised = False

    async def __aenter__(self):
        self.handle = self.loop.create_task(do_after_sleep(1, attempt_add_reaction, self.message,
                                                           "\N{BLACK RIGHT-POINTING TRIANGLE}"))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.handle:
            self.handle.cancel()

        # no exception, check mark
        if not exc_val:
            await attempt_add_reaction(self.message, "\N{WHITE HEAVY CHECK MARK}")
            return

        self.raised = True

        if isinstance(exc_val, (asyncio.TimeoutError, subprocess.TimeoutExpired)):
            # timed out, alarm clock
            await attempt_add_reaction(self.message, "\N{ALARM CLOCK}")
        elif isinstance(exc_val, SyntaxError):
            # syntax error, single exclamation mark
            await attempt_add_reaction(self.message, "\N{HEAVY EXCLAMATION MARK SYMBOL}")
        else:
            # other error, double exclamation mark
            await attempt_add_reaction(self.message, "\N{DOUBLE EXCLAMATION MARK}")


class ReplResponseReactor(ReactionProcedureTimer):
    """
    Extension of the ReactionProcedureTimer that absorbs errors, sending tracebacks.
    """

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)

        # nothing went wrong, who cares lol
        if not exc_val:
            return

        if isinstance(exc_val, (SyntaxError, asyncio.TimeoutError, subprocess.TimeoutExpired)):
            # short traceback, send to channel
            await send_traceback(self.message.channel, 0, exc_type, exc_val, exc_tb)
        else:
            # this traceback likely needs more info, so increase verbosity, and DM it instead.
            await send_traceback(self.message.author, 8, exc_type, exc_val, exc_tb)

        return True  # the exception has been handled
