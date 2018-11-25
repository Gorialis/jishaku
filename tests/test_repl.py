# -*- coding: utf-8 -*-

"""
jishaku.repl internal test
~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2018 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import random
import unittest

from jishaku.repl import AsyncCodeExecutor, Scope, get_parent_var


class ReplInternalsTest(unittest.TestCase):

    def test_scope_var(self):
        for _ in range(10):
            hidden_variable = random.randint(0, 1000000)
            test = self.upper_method()

            self.assertEqual(hidden_variable, test)

            del hidden_variable

            test = self.upper_method()
            self.assertEqual(test, None)

            self.assertEqual(get_parent_var('unittest', global_ok=True), unittest)

    @staticmethod
    def upper_method():
        return get_parent_var('hidden_variable')


class ReplAsyncExecutorTest(unittest.TestCase):

    def test_executor(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.internal_test())

    async def internal_test(self):
        scope = Scope()

        return_data = []
        async for result in AsyncCodeExecutor('3 + 4', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1)
        self.assertEqual(return_data[0], 7)

        return_data = []
        async for result in AsyncCodeExecutor('return 3 + 9', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1)
        self.assertEqual(return_data[0], 12)

        return_data = []
        async for result in AsyncCodeExecutor('b = 12 + 82', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1)
        self.assertEqual(return_data[0], None)

        return_data = []
        async for result in AsyncCodeExecutor('b', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1)
        self.assertEqual(return_data[0], 94)

        scope.update_globals({'d': 41})

        return_data = []
        async for result in AsyncCodeExecutor('c = d + 7; c', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1)
        self.assertEqual(return_data[0], 48)

        return_data = []
        async for result in AsyncCodeExecutor('yield 30; yield 40', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 2)
        self.assertEqual(return_data[0], 30)
        self.assertEqual(return_data[1], 40)

        return_data = []
        async for result in AsyncCodeExecutor('yield 60; 70', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 2)
        self.assertEqual(return_data[0], 60)
        self.assertEqual(return_data[1], 70)

        return_data = []
        async for result in AsyncCodeExecutor('90; 100', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1)
        self.assertEqual(return_data[0], 100)

        arg_dict = {
            '_cool_data': 45,
            '_not_so_cool': 400
        }
        return_data = []
        async for result in AsyncCodeExecutor('_cool_data + _not_so_cool', scope, arg_dict=arg_dict):
            return_data.append(result)

        self.assertEqual(len(return_data), 1)
        self.assertEqual(return_data[0], 445)

        scope.clean()

        hit_exception = False
        try:
            async for result in AsyncCodeExecutor('_cool_data', scope):
                pass
        except NameError:
            hit_exception = True

        self.assertTrue(hit_exception)

        scope2 = Scope()
        scope2.update(scope)

        self.assertEqual(scope.globals, scope2.globals)
        self.assertEqual(scope.locals, scope2.locals)

        scope.update_locals({'e': 7})

        self.assertIn('e', scope.locals)
        self.assertNotIn('e', scope2.locals)
