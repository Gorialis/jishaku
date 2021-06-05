# -*- coding: utf-8 -*-

"""
jishaku subclassing functionality test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import pytest
import utils
from discord.ext import commands


@pytest.fixture(
    scope='module',
    params=[
        # Subclass 1 (Feature)
        ("tests.subclassed_module_1", "Magnet1", "overridden with a third party feature", commands.Bot, {}),
        ("tests.subclassed_module_1", "Magnet1", "overridden with a third party feature", commands.Bot, {"shard_id": 0, "shard_count": 2}),
        ("tests.subclassed_module_1", "Magnet1", "overridden with a third party feature", commands.AutoShardedBot, {}),
        # Subclass 2 (direct)
        ("tests.subclassed_module_2", "Magnet2", "overridden directly", commands.Bot, {}),
        ("tests.subclassed_module_2", "Magnet2", "overridden directly", commands.Bot, {"shard_id": 0, "shard_count": 2}),
        ("tests.subclassed_module_2", "Magnet2", "overridden directly", commands.AutoShardedBot, {}),
        # Test that the original still works after the load test
        ("jishaku", "Jishaku", "Module was loaded", commands.Bot, {}),
        ("jishaku", "Jishaku", "Module was loaded", commands.Bot, {"shard_id": 0, "shard_count": 2}),
        ("jishaku", "Jishaku", "Module was loaded", commands.AutoShardedBot, {}),
    ],
    ids=[
        "Feature-based subclass (Bot, unsharded)",
        "Feature-based subclass (Bot, sharded)",
        "Feature-based subclass (AutoShardedBot)",
        "direct subclass (Bot, unsharded)",
        "direct subclass (Bot, sharded)",
        "direct subclass (AutoShardedBot)",
        "native (Bot, unsharded)",
        "native (Bot, sharded)",
        "native (AutoShardedBot)"
    ]
)
def bot(request):
    b = request.param[3]('?', **request.param[4])
    b.load_extension(request.param[0])

    b.test_cog = request.param[1]
    b.test_predicate = request.param[2]

    yield b

    b.unload_extension(request.param[0])
    b.loop.run_until_complete(b.close())


@utils.run_async
async def test_commands(bot):
    cog = bot.get_cog(bot.test_cog)

    assert cog is not None

    # test 'jsk'
    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk').callback(cog, ctx)

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert bot.test_predicate in text
