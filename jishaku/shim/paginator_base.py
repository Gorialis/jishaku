# -*- coding: utf-8 -*-

"""
jishaku.paginators (non-shim dependencies)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Paginator-related tools and interfaces for Jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import collections

# emoji settings, this sets what emoji are used for PaginatorInterface
EmojiSettings = collections.namedtuple('EmojiSettings', 'start back forward end close')

EMOJI_DEFAULT = EmojiSettings(
    start="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
    back="\N{BLACK LEFT-POINTING TRIANGLE}",
    forward="\N{BLACK RIGHT-POINTING TRIANGLE}",
    end="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
    close="\N{BLACK SQUARE FOR STOP}"
)
