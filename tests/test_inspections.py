# -*- coding: utf-8 -*-

"""
jishaku.inspections test
~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import collections  # for __iadd__ test

import discord
import pytest

from jishaku.repl.inspections import all_inspections
from tests.utils import sentinel


@pytest.mark.parametrize(
    "target",
    [
        4,
        discord.Client,  # cover type subclasses
        tuple,  # cover many-subclass truncation
        [False, 1, "2", 3.0],  # cover content types
        collections.Counter,  # cover inplace operators
        sentinel  # cover current-working-directory inspections
    ]
)
def test_object_inspection(target):
    for _, _ in all_inspections(target):
        pass
