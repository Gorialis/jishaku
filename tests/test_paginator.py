# -*- coding: utf-8 -*-

"""
jishaku converter test
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect
from io import BytesIO

import pytest

from jishaku.paginators import FilePaginator, WrappedPaginator


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

# TODO: Write test for interactions-based paginator interface
