# -*- coding: utf-8 -*-

"""
jishaku.cog loadability and functionality test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio

import pytest
import utils
from discord.ext import commands


@pytest.fixture(
    scope='module',
    params=[
        ("jishaku", commands.Bot, {}),
        ("jishaku", commands.Bot, {"shard_id": 0, "shard_count": 2}),
        ("jishaku", commands.AutoShardedBot, {}),
        ("jishaku.cog", commands.Bot, {}),
        ("jishaku.cog", commands.Bot, {"shard_id": 0, "shard_count": 2}),
        ("jishaku.cog", commands.AutoShardedBot, {}),
    ],
    ids=[
        "jishaku (Bot, unsharded)",
        "jishaku (Bot, sharded)",
        "jishaku (AutoShardedBot)",
        "jishaku.cog (Bot, unsharded)",
        "jishaku.cog (Bot, sharded)",
        "jishaku.cog (AutoShardedBot)"
    ]
)
def bot(request):
    b = request.param[1]('?', **request.param[2])
    b.load_extension(request.param[0])

    yield b

    b.unload_extension(request.param[0])
    b.loop.run_until_complete(b.close())


def test_loads(bot):
    assert bot.get_cog("Jishaku")
    assert isinstance(bot.get_cog("Jishaku"), commands.Cog)

    assert bot.get_command("jsk")
    assert isinstance(bot.get_command("jsk"), commands.Command)


def test_cog_attributes(bot):
    cog = bot.get_cog("Jishaku")

    cog.retain = False
    assert cog.scope is not cog.scope, "Scope property should give new scopes on no retain"

    cog.retain = True
    assert cog.scope is cog.scope, "Scope property should be consistent on retain"

    assert not cog.tasks

    with cog.submit("mock 1") as cmd_task:
        assert len(cog.tasks) == 1

        assert cmd_task.index == 1
        assert cmd_task.ctx == "mock 1"
        assert cmd_task.task is None

    assert not cog.tasks

    with cog.submit("mock 2") as cmd_task:
        assert len(cog.tasks) == 1

        assert cmd_task.index == 2
        assert cmd_task.ctx == "mock 2"
        assert cmd_task.task is None

    assert not cog.tasks


@utils.run_async
async def test_cog_check(bot):
    cog = bot.get_cog("Jishaku")

    with utils.mock_ctx() as ctx:
        with utils.mock_coro(ctx.bot, 'is_owner'):
            ctx.bot.is_owner.coro.return_value = True

            assert await cog.cog_check(ctx)

            ctx.bot.is_owner.coro.return_value = False

            with pytest.raises(commands.NotOwner):
                await cog.cog_check(ctx)


@utils.run_async
async def test_commands(bot):
    cog = bot.get_cog("Jishaku")

    # test 'jsk'
    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk').callback(cog, ctx)

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "Module was loaded" in text

    # test 'jsk hide' and 'jsk show'
    cog.jsk.hidden = False

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk hide').callback(cog, ctx)

        assert cog.jsk.hidden

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "now hidden" in text

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk hide').callback(cog, ctx)

        assert cog.jsk.hidden

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "already hidden" in text

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk show').callback(cog, ctx)

        assert not cog.jsk.hidden

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "now visible" in text

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk show').callback(cog, ctx)

        assert not cog.jsk.hidden

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "already visible" in text

    # test 'jsk tasks'
    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk tasks').callback(cog, ctx)

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "No currently running tasks" in text

    with utils.mock_ctx() as ctx:
        with cog.submit(ctx):
            interface = await bot.get_command('jsk tasks').callback(cog, ctx)

            ctx.send.assert_called_once()

            interface.task.cancel()

    # test 'jsk cancel'
    with utils.mock_ctx() as ctx:
        # test explicit
        with cog.submit(ctx) as command_task:
            with pytest.raises(asyncio.CancelledError):
                await bot.get_command('jsk cancel').callback(cog, ctx, index=command_task.index)
                await asyncio.sleep(0.1)

            ctx.send.assert_called_once()
            text = ctx.send.call_args[0][0]
            assert f"Cancelled task {command_task.index}" in text

    with utils.mock_ctx() as ctx:
        # test implicit
        with cog.submit(ctx) as command_task:
            with pytest.raises(asyncio.CancelledError):
                await bot.get_command('jsk cancel').callback(cog, ctx, index=-1)
                await asyncio.sleep(0.1)

            ctx.send.assert_called_once()
            text = ctx.send.call_args[0][0]
            assert f"Cancelled task {command_task.index}" in text

    with utils.mock_ctx() as ctx:
        # test unknown task
        with cog.submit(ctx) as command_task:
            await bot.get_command('jsk cancel').callback(cog, ctx, index=123456789012345678)

            ctx.send.assert_called_once()
            text = ctx.send.call_args[0][0]
            assert "Unknown task" in text

    with utils.mock_ctx() as ctx:
        # test no tasks
        await bot.get_command('jsk cancel').callback(cog, ctx, index=123456789012345678)

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "No tasks" in text

    # test 'jsk retain'
    cog.retain = False

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk retain').callback(cog, ctx, toggle=True)

        assert cog.retain

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "is ON" in text

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk retain').callback(cog, ctx, toggle=True)

        assert cog.retain

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "already set to ON" in text

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk retain').callback(cog, ctx, toggle=None)

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "is set to ON" in text

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk retain').callback(cog, ctx, toggle=False)

        assert not cog.retain

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "is OFF" in text

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk retain').callback(cog, ctx, toggle=False)

        assert not cog.retain

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "already set to OFF" in text

    with utils.mock_ctx() as ctx:
        await bot.get_command('jsk retain').callback(cog, ctx, toggle=None)

        ctx.send.assert_called_once()
        text = ctx.send.call_args[0][0]
        assert "is set to OFF" in text
