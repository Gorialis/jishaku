# -*- coding: utf-8 -*-

"""
jishaku.hljs test
~~~~~~~~~~~~~~~~~

:copyright: (c) 2018 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import unittest

from jishaku.hljs import get_language


class HighlightJSTest(unittest.TestCase):
    def test_hljs(self):
        self.assertEqual(get_language('base.py'), 'py')
        self.assertEqual(get_language('config.yml'), 'yml')
        self.assertEqual(get_language('requirements.txt'), '')
        self.assertEqual(get_language('#!/usr/bin/env python'), 'python')
        self.assertEqual(get_language('#!/usr/bin/unknown'), '')
