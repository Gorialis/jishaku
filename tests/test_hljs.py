# -*- coding: utf-8 -*-

"""
jishaku.hljs test
~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import pytest

from jishaku.hljs import get_language


@pytest.mark.parametrize(
    ("filename", "language"),
    [
        ('base.py', 'py'),
        ('config.yml', 'yml'),
        ('requirements.txt', ''),
        ('#!/usr/bin/env python', 'python'),
        ('#!/usr/bin/unknown', '')
    ]
)
def test_hljs(filename, language):
    assert get_language(filename) == language
