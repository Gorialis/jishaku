# -*- coding: utf-8 -*-

"""
jishaku.inspections test
~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import collections  # for __iadd__ test

import discord

from jishaku.repl.inspections import all_inspections


def test_object_inspection():
    inspections = list(all_inspections(4))
    inspections_2 = list(all_inspections(discord.Client))

    assert len(inspections_2) >= len(inspections)

    # cover subclasses
    for _, _ in all_inspections(tuple):
        pass

    # cover cwd file locations
    for _, _ in all_inspections(test_object_inspection):
        pass

    # cover content types
    for _, _ in all_inspections([False, 1, "2", 3.0]):
        pass

    # test inplace operators
    for _, _ in all_inspections(collections.Counter):
        pass
