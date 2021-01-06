# -*- coding: utf-8 -*-

"""
jishaku.models tests
~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import utils

from jishaku.models import copy_context_with


@utils.run_async
async def test_context_copy():
    with utils.mock_ctx() as ctx:
        await copy_context_with(ctx, author=1, channel=2, content=3)

        ctx.bot.get_context.assert_called_once()
        alt_message = ctx.bot.get_context.call_args[0][0]

        alt_message._update.assert_called_once()
        assert alt_message._update.call_args[0] == ({"content": 3},)
