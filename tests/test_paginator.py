# -*- coding: utf-8 -*-

"""
jishaku converter test
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect
import unittest
from io import BytesIO

import discord
from discord.ext import commands

from jishaku.paginators import FilePaginator, PaginatorEmbedInterface, PaginatorInterface, WrappedPaginator


class PaginatorTest(unittest.TestCase):
    def test_file_paginator(self):

        base_text = inspect.cleandoc("""
        #!/usr/bin/env python
        # -*- coding: utf-8 -*-
        pass  # \u3088\u308d\u3057\u304f
        """)

        # test standard encoding
        pages = FilePaginator(BytesIO(base_text.encode("utf-8"))).pages

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0], f"```python\n{base_text}\n```")

        # test linespan
        pages = FilePaginator(BytesIO(base_text.encode("utf-8")), line_span=(2, 2)).pages

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0], f"```python\n# -*- coding: utf-8 -*-\n```")

        # test reception to encoding hint
        base_text = inspect.cleandoc("""
        #!/usr/bin/env python
        # -*- coding: cp932 -*-
        pass  # \u3088\u308d\u3057\u304f
        """)

        pages = FilePaginator(BytesIO(base_text.encode("cp932"))).pages

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0], f"```python\n{base_text}\n```")

        # test without encoding hint
        raised = False

        try:
            FilePaginator(BytesIO("\u3088\u308d\u3057\u304f".encode("cp932")))
        except UnicodeDecodeError:
            raised = True

        self.assertTrue(raised)

        # test with wrong encoding hint
        raised = False

        try:
            FilePaginator(BytesIO("-*- coding: utf-8 -*-\n\u3088\u308d\u3057\u304f".encode("cp932")))
        except UnicodeDecodeError:
            raised = True

        self.assertTrue(raised)

        # test OOB
        raised = False

        try:
            FilePaginator(BytesIO("one\ntwo\nthree\nfour".encode('utf-8')), line_span=(-1, 20))
        except ValueError:
            raised = True

        self.assertTrue(raised)

    def test_wrapped_paginator(self):
        paginator = WrappedPaginator(max_size=200)
        paginator.add_line("abcde " * 50)
        self.assertEqual(len(paginator.pages), 2)

    def test_paginator_interface(self):
        bot = commands.Bot('?')

        with open(__file__, 'rb') as fp:
            paginator = FilePaginator(fp, max_size=200)

        interface = PaginatorInterface(bot, paginator)

        self.assertEqual(interface.pages, paginator.pages)
        self.assertEqual(interface.page_count, len(paginator.pages))

        self.assertGreater(interface.page_size, 200)
        self.assertLess(interface.page_size, interface.max_page_size)

        send_kwargs = interface.send_kwargs

        self.assertIsInstance(send_kwargs, dict)
        self.assertIn('content', send_kwargs)

        content = send_kwargs['content']

        self.assertIsInstance(content, str)
        self.assertLessEqual(len(content), interface.page_size)

        self.assertEqual(interface.display_page, 0)

        # pages have been closed, so adding a line should make a new page
        old_page_count = interface.page_count

        bot.loop.run_until_complete(interface.add_line('a' * 150))

        self.assertGreater(interface.page_count, old_page_count)

        # push the page to the end (rounded into bounds)
        interface.display_page = 999
        old_display_page = interface.display_page

        self.assertEqual(interface.pages, paginator.pages)

        # page closed, so create new page
        bot.loop.run_until_complete(interface.add_line('b' * 150))

        # ensure page has followed tail
        self.assertGreater(interface.display_page, old_display_page)

        # testing with embed interface
        embed_interface = PaginatorEmbedInterface(bot, paginator)

        self.assertEqual(embed_interface.pages[0], interface.pages[0])

        send_kwargs = embed_interface.send_kwargs

        self.assertIsInstance(send_kwargs, dict)
        self.assertIn('embed', send_kwargs)

        embed = send_kwargs['embed']

        self.assertIsInstance(embed, discord.Embed)

        description = embed.description

        self.assertTrue(content.startswith(description))

        # check for raise on too large page size
        raised = False

        try:
            PaginatorInterface(None, commands.Paginator(max_size=2000))
        except ValueError:
            raised = True

        self.assertTrue(raised)

        # check for raise on not-paginator
        raised = False

        try:
            PaginatorInterface(None, 4)
        except TypeError:
            raised = True

        self.assertTrue(raised)

        bot.loop.run_until_complete(bot.close())
