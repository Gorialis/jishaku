# -*- coding: utf-8 -*-

"""
jishaku converter test
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect
from io import BytesIO

import discord
import pytest
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
    assert pages[0] == f"```python\n# -*- coding: utf-8 -*-\n```"

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


def test_paginator_interface():
    bot = commands.Bot('?')

    with open(__file__, 'rb') as fp:
        paginator = FilePaginator(fp, max_size=200)

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

    bot.loop.run_until_complete(interface.add_line('a' * 150))

    assert interface.page_count > old_page_count

    # push the page to the end (rounded into bounds)
    interface.display_page = 999
    old_display_page = interface.display_page

    assert interface.pages == paginator.pages

    # page closed, so create new page
    bot.loop.run_until_complete(interface.add_line('b' * 150))

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
