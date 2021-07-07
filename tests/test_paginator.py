# -*- coding: utf-8 -*-

"""
jishaku converter test
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import inspect
from io import BytesIO

import discord
import pytest
import utils
from discord.ext import commands

from jishaku.paginators import FilePaginator, PaginatorEmbedInterface, PaginatorInterface, WrappedPaginator


def test_file_paginator():

    base_text = inspect.cleandoc("""
    #!/usr/bin/env python
    # -*- coding: utf-8 -*-
    pass  # \u3088\u308d\u3057\u304f
    """)

    # test standard encoding
    pages = FilePaginator(BytesIO(base_text.encode("utf-8"))).pages

    assert len(pages) == 1
    assert pages[0] == f"```python\n{base_text}\n```"

    # test linespan
    pages = FilePaginator(BytesIO(base_text.encode("utf-8")), line_span=(2, 2)).pages

    assert len(pages) == 1
    assert pages[0] == "```python\n# -*- coding: utf-8 -*-\n```"

    # test reception to encoding hint
    base_text = inspect.cleandoc("""
    #!/usr/bin/env python
    # -*- coding: cp932 -*-
    pass  # \u3088\u308d\u3057\u304f
    """)

    pages = FilePaginator(BytesIO(base_text.encode("cp932"))).pages

    assert len(pages) == 1
    assert pages[0] == f"```python\n{base_text}\n```"

    # test without encoding hint
    with pytest.raises(UnicodeDecodeError):
        FilePaginator(BytesIO("\u3088\u308d\u3057\u304f".encode("cp932")))

    # test with wrong encoding hint
    with pytest.raises(UnicodeDecodeError):
        FilePaginator(BytesIO("-*- coding: utf-8 -*-\n\u3088\u308d\u3057\u304f".encode("cp932")))

    # test OOB
    with pytest.raises(ValueError):
        FilePaginator(BytesIO("one\ntwo\nthree\nfour".encode('utf-8')), line_span=(-1, 20))


def test_wrapped_paginator():
    paginator = WrappedPaginator(max_size=200)
    paginator.add_line("abcde " * 50)
    assert len(paginator.pages) == 2

    paginator = WrappedPaginator(max_size=200, include_wrapped=False)
    paginator.add_line("abcde " * 50)
    assert len(paginator.pages) == 2


@pytest.mark.skipif(
    discord.version_info >= (2, 0, 0),
    reason="Tests with the reaction model of the paginator interface"
)
@utils.run_async
async def test_paginator_interface_reactions():
    bot = commands.Bot('?')

    with open(__file__, 'rb') as file:
        paginator = FilePaginator(file, max_size=200)

    interface = PaginatorInterface(bot, paginator)

    assert interface.pages == paginator.pages
    assert interface.page_count == len(paginator.pages)

    assert interface.page_size > 200
    assert interface.page_size < interface.max_page_size

    send_kwargs = interface.send_kwargs

    assert isinstance(send_kwargs, dict)
    assert 'content' in send_kwargs

    content = send_kwargs['content']

    assert isinstance(content, str)
    assert len(content) <= interface.page_size

    assert interface.display_page == 0

    # pages have been closed, so adding a line should make a new page
    old_page_count = interface.page_count

    await interface.add_line('a' * 150)

    assert interface.page_count > old_page_count

    # push the page to the end (rounded into bounds)
    interface.display_page = 999
    old_display_page = interface.display_page

    assert interface.pages == paginator.pages

    # page closed, so create new page
    await interface.add_line('b' * 150)

    # ensure page has followed tail
    assert interface.display_page > old_display_page

    # testing with embed interface
    embed_interface = PaginatorEmbedInterface(bot, paginator)

    assert embed_interface.pages[0] == interface.pages[0]

    send_kwargs = embed_interface.send_kwargs

    assert isinstance(send_kwargs, dict)
    assert 'embed' in send_kwargs

    embed = send_kwargs['embed']

    assert isinstance(embed, discord.Embed)

    description = embed.description

    assert content.startswith(description)

    # check for raise on too large page size
    with pytest.raises(ValueError):
        PaginatorInterface(None, commands.Paginator(max_size=2000))

    # check for raise on not-paginator
    with pytest.raises(TypeError):
        PaginatorInterface(None, 4)

    paginator = commands.Paginator(max_size=100)
    for _ in range(100):
        paginator.add_line("test text")

    # test interfacing
    with utils.mock_ctx(bot) as ctx:
        interface = PaginatorInterface(bot, paginator)

        assert not interface.closed

        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        assert interface.page_count > 1
        assert not interface.closed

        interface.message.id = utils.sentinel()

        current_page = interface.display_page

        payload = {
            'message_id': interface.message.id,
            'user_id': ctx.author.id,
            'channel_id': ctx.channel.id,
            'guild_id': ctx.guild.id
        }

        # push right button
        emoji = discord.PartialEmoji(
            animated=False,
            name="\N{BLACK RIGHT-POINTING TRIANGLE}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            discord.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if discord.version_info >= (1, 3) else
            discord.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.display_page > current_page
        assert not interface.closed

        current_page = interface.display_page

        # push left button
        emoji = discord.PartialEmoji(
            animated=False,
            name="\N{BLACK LEFT-POINTING TRIANGLE}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            discord.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if discord.version_info >= (1, 3) else
            discord.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.display_page < current_page
        assert not interface.closed

        # push last page button
        emoji = discord.PartialEmoji(
            animated=False,
            name="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            discord.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if discord.version_info >= (1, 3) else
            discord.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.display_page == interface.page_count - 1
        assert not interface.closed

        # push first page button
        emoji = discord.PartialEmoji(
            animated=False,
            name="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            discord.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if discord.version_info >= (1, 3) else
            discord.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.display_page == 0
        assert not interface.closed

        # push close button
        emoji = discord.PartialEmoji(
            animated=False,
            name="\N{BLACK SQUARE FOR STOP}",
            id=None
        )
        bot.dispatch(
            'raw_reaction_add',
            discord.RawReactionActionEvent(payload, emoji, 'REACTION_ADD')
            if discord.version_info >= (1, 3) else
            discord.RawReactionActionEvent(payload, emoji)
        )

        await asyncio.sleep(0.1)

        assert interface.closed
        ctx.send.coro.return_value.delete.assert_called_once()

    # test resend, no delete
    with utils.mock_ctx(bot) as ctx:
        interface = PaginatorInterface(bot, paginator)

        assert not interface.closed

        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        assert interface.page_count > 1
        assert not interface.closed

        # resend
        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        ctx.send.coro.return_value.delete.assert_not_called()

        interface.task.cancel()
        await asyncio.sleep(0.1)

        assert interface.closed

    # test resend, delete
    with utils.mock_ctx(bot) as ctx:
        interface = PaginatorInterface(bot, paginator, delete_message=True)

        assert not interface.closed

        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        assert interface.page_count > 1
        assert not interface.closed

        # resend
        await interface.send_to(ctx)

        await asyncio.sleep(0.1)
        await interface.add_line("test text")

        ctx.send.coro.return_value.delete.assert_called_once()

        interface.task.cancel()
        await asyncio.sleep(0.1)

        assert interface.closed

# TODO: Write test for interactions-based paginator interface
