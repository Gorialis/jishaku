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

import asyncio
import logging
import sys
import time
import typing
import uuid

import click
import discord
from discord.ext import commands

LOG_FORMAT: logging.Formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
LOG_STREAM: logging.Handler = logging.StreamHandler(stream=sys.stdout)
LOG_STREAM.setFormatter(LOG_FORMAT)


async def entry(bot: commands.Bot, *args: typing.Any, **kwargs: typing.Any):
    """
    Async entrypoint for 2.0a compatibility
    """

    await discord.utils.maybe_coroutine(bot.load_extension, 'jishaku')  # type: ignore

    try:
        await bot.start(*args, **kwargs)
    except KeyboardInterrupt:
        pass


@click.command()
@click.argument('intents', nargs=-1)
@click.argument('token')
@click.option('--log-level', '-v', default='DEBUG')
@click.option('--log-file', '-l', default=None)
def entrypoint(intents: typing.Iterable[str], token: str, log_level: str, log_file: typing.Optional[str] = None):
    """
    Entrypoint accessible through `python -m jishaku <TOKEN>`

    Specify intents using + and - before the token
    E.g.:
        -m jishaku -- +all -message_content <TOKEN>
    Arguments are applied in order.
    You can also set log level and output to a file:
        -m jishaku --log-level INFO --log-file bot.log -- +all <TOKEN>
    """

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    logger.addHandler(LOG_STREAM)

    if log_file:
        log_file_handler: logging.Handler = logging.FileHandler(filename=log_file, encoding='utf-8', mode='a')
        log_file_handler.setFormatter(LOG_FORMAT)
        logger.addHandler(log_file_handler)

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

    unique_id = str(uuid.uuid4())
    logging.getLogger('jishaku.__main__').critical(
        'Generated a unique UUID for this session: %s'
        '\nYou can use Jishaku with your bot once it starts using `%s::jsk <subcommand>`'
        '\nIf you have no message content, you can prefix it with the mention: `@Bot %s::jsk <subcommand>`',
        unique_id, unique_id, unique_id
    )

    time.sleep(10)

    def prefix(bot: commands.Bot, _: discord.Message) -> typing.List[str]:
        return [
            f'{unique_id}::',
            f'<@{bot.user.id}> {unique_id}::',  # type: ignore
            f'<@!{bot.user.id}> {unique_id}::',  # type: ignore
        ]

    bot = commands.Bot(prefix, intents=intents_class)

    if discord.version_info >= (2, 0, 0):
        asyncio.run(entry(bot, token))
    else:
        bot.load_extension('jishaku')  # type: ignore
        bot.run(token)  # type: ignore


if __name__ == '__main__':
    entrypoint()  # pylint: disable=no-value-for-parameter
