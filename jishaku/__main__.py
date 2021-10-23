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
import typing

import click
import discord
from discord.ext import commands

LOG_FORMAT: logging.Formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
LOG_STREAM: logging.Handler = logging.StreamHandler(stream=sys.stdout)
LOG_STREAM.setFormatter(LOG_FORMAT)


@click.command()
@click.argument('intents', nargs=-1)
@click.argument('token')
def entrypoint(intents: typing.Iterable[str], token: str):
    """
    Entrypoint accessible through `python -m jishaku <TOKEN>`
    """

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(LOG_STREAM)

    intents_class = discord.Intents.default()
    all_intents = [name for name, _ in discord.Intents.all()]
    default_intents = [name for name, value in discord.Intents.default() if value]

    for intent in intents:
        if not intent.startswith(('+', '-')):
            raise click.BadArgumentUsage(
                f"Intent argument {intent} is invalid; intents must start with + or - (e.g. +all)"
            )

        name = intent[1:].lower()
        value = intent[0] == "+"

        if name in all_intents:
            setattr(intents_class, name, value)
        elif name == 'all':
            intents_class = discord.Intents.all() if value else discord.Intents.none()
        elif name == 'default':
            for default_intent in default_intents:
                setattr(intents_class, default_intent, value)
        else:
            # pylint: disable=superfluous-parens
            # pylint you are wrong!! it breaks if you remove those!!
            maybe_you_meant = [
                intent_name for intent_name in all_intents
                if (name[1:-1] if len(name) > 3 else name) in intent_name
            ]
            # pylint: enable=superfluous-parens

            if maybe_you_meant:
                raise click.BadArgumentUsage(
                    f"Intent argument {intent} is invalid; the intent {name} was not found."
                    f" Maybe you meant {intent[0]}{maybe_you_meant[0]}?"
                )

            raise click.BadArgumentUsage(
                f"Intent argument {intent} is invalid; the intent {name} was not found."
            )

    bot = commands.Bot(commands.when_mentioned, intents=intents_class)
    bot.load_extension('jishaku')
    bot.run(token)


if __name__ == '__main__':
    entrypoint()  # pylint: disable=no-value-for-parameter
