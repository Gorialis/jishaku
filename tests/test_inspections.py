# -*- coding: utf-8 -*-

"""
jishaku.inspections test
~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2018 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import collections  # for __iadd__ test
import unittest

import discord

from jishaku.repl.inspections import all_inspections


class InspectionTest(unittest.TestCase):
    def test_object_inspection(self):
        inspections = []

        for x, y in all_inspections(4):
            inspections.append((x, y))

        inspections_2 = []

        for x, y in all_inspections(discord.Client):
            inspections_2.append((x, y))

        self.assertGreaterEqual(len(inspections_2), len(inspections))

        # cover subclasses
        for _, _ in all_inspections(tuple):
            pass

        # cover cwd file locations
        for _, _ in all_inspections(InspectionTest):
            pass

        # cover content types
        for _, _ in all_inspections([False, 1, "2", 3.0]):
            pass

        # test inplace operators
        for _, _ in all_inspections(collections.Counter):
            pass
