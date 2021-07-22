# -*- coding: utf-8 -*-

"""
jishaku.__main__
~~~~~~~~~~~~~~~~~

This is an entrypoint that sets up a basic Bot with Jishaku.
It has console logging set up and uses a mention prefix.

This is mostly intended to be a quick means to have a debuggable bot from a token.
It can be used to perform manual administrative actions as the bot, or to test Jishaku itself.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import logging
import sys

import click
from discord.ext import commands

LOG_FORMAT: logging.Formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
LOG_STREAM: logging.Handler = logging.StreamHandler(stream=sys.stdout)
LOG_STREAM.setFormatter(LOG_FORMAT)


@click.command()
@click.argument('token')
def entrypoint(token: str):
    """
    Entrypoint accessible through `python -m jishaku <TOKEN>`
    """

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(LOG_STREAM)

    bot = commands.Bot(commands.when_mentioned)
    bot.load_extension('jishaku')
    bot.run(token)


if __name__ == '__main__':
    entrypoint()  # pylint: disable=no-value-for-parameter
