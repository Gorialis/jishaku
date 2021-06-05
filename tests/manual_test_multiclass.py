# -*- coding: utf-8 -*-

"""
jishaku manual multiclass test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a manually-activated test designed to determine if independent
subclasses of Jishaku can run simultaneously on the same event loop
without conflicting with eachother.

Execute this test from the repository using:
python -m tests.manual_test_multiclass "$BOT_TOKEN"

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import logging
import logging.handlers
import sys
import typing

import click
from discord.ext import commands

LOADABLES = (
    ('j!1 ', 'tests.subclassed_module_1'),
    ('j!2 ', 'tests.subclassed_module_2'),
    ('j!n ', 'jishaku'),
)


async def async_entrypoint(token):
    bots: typing.List[commands.Bot] = []

    for prefix, extension in LOADABLES:
        bot = commands.Bot(prefix)
        bot.load_extension(extension)

        bots.append(bot)

    # Connect all bots
    # When any bot exits, exit all bots
    await asyncio.wait([
        asyncio.create_task(bot.start(token))
        for bot in bots
    ], return_when=asyncio.FIRST_COMPLETED)

    for bot in bots:
        if not bot.is_closed():
            await bot.close()


@click.command()
@click.argument('token')
def entrypoint(token):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    log_format = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
    log_stream = logging.StreamHandler(stream=sys.stdout)

    log_stream.setFormatter(log_format)
    logger.addHandler(log_stream)

    asyncio.run(async_entrypoint(token))


if __name__ == "__main__":
    entrypoint()
