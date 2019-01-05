# -*- coding: utf-8 -*-

"""
jishaku.repl internal test
~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import inspect
import random
import sys
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

    async def add_numbers(self, one, two):
        return one + two

    async def internal_test(self):
        scope = Scope()

        return_data = []
        async for result in AsyncCodeExecutor('3 + 4', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1, msg="Checking eval produces single result")
        self.assertEqual(return_data[0], 7, msg="Checking eval result is consistent")

        return_data = []
        async for result in AsyncCodeExecutor('return 3 + 9', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1, msg="Checking manual return produces single result")
        self.assertEqual(return_data[0], 12, msg="Checking return result is consistent")

        return_data = []
        async for result in AsyncCodeExecutor('b = 12 + 82', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1, msg="Checking that assignment returns")
        self.assertIsNone(return_data[0], msg="Checking assignment returns None")

        return_data = []
        async for result in AsyncCodeExecutor('b', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1, msg="Checking variable eval returns")
        self.assertEqual(return_data[0], 94, msg="Checking retained variable consistent")

        scope.update_globals({'d': 41})

        return_data = []
        async for result in AsyncCodeExecutor('c = d + 7; c', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1, msg="Checking multi-expression implicitly returns")
        self.assertEqual(return_data[0], 48, msg="Checking last expression return is consistent")

        return_data = []
        async for result in AsyncCodeExecutor('yield 30; yield 40', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 2, msg="Checking two yields returns two results")
        self.assertEqual(return_data[0], 30, msg="Checking first yield consistency")
        self.assertEqual(return_data[1], 40, msg="Checking second yield consistency")

        return_data = []
        async for result in AsyncCodeExecutor('yield 60; 70', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 2, msg="Checking multi-statement implicitly yields")
        self.assertEqual(return_data[0], 60, msg="Checking explicit yield consistent")
        self.assertEqual(return_data[1], 70, msg="Checking implicit yield consistent")

        return_data = []
        async for result in AsyncCodeExecutor('90; 100', scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1, msg="Checking multi-statement implicitly returns")
        self.assertEqual(return_data[0], 100, msg="Checking implicit return consistent")

        arg_dict = {
            '_cool_data': 45,
            '_not_so_cool': 400
        }
        return_data = []
        async for result in AsyncCodeExecutor('_cool_data + _not_so_cool', scope, arg_dict=arg_dict):
            return_data.append(result)

        self.assertEqual(len(return_data), 1, msg="Checking arg dictionary expression returned")
        self.assertEqual(return_data[0], 445, msg="Checking arg dictionary expression consistent")

        scope.clean()

        hit_exception = False
        try:
            async for result in AsyncCodeExecutor('_cool_data', scope):
                pass
        except NameError:
            hit_exception = True

        self.assertTrue(hit_exception, msg="Checking private locals removed")

        scope2 = Scope()
        scope2.update(scope)

        self.assertEqual(scope.globals, scope2.globals, msg="Checking scope globals copied")
        self.assertEqual(scope.locals, scope2.locals, msg="Checking scope locals copied")

        scope.update_locals({'e': 7})

        self.assertIn('e', scope.locals, msg="Checking scope locals updated")
        self.assertNotIn('e', scope2.locals, msg="Checking scope clone locals not updated")

        scope.clean()

        codeblock = inspect.cleandoc("""
        def ensure_builtins():
            return ValueError
        """)

        async for result in AsyncCodeExecutor(codeblock, scope):
            pass

        scope.clean()

        self.assertIn('ensure_builtins', scope.globals, msg="Checking function remains defined")
        self.assertTrue(callable(scope.globals['ensure_builtins']), msg="Checking defined is callable")
        self.assertEqual(scope.globals['ensure_builtins'](), ValueError, msg="Checking defined retuurn consistent")

        if sys.version_info >= (3, 7):
            codeblock = inspect.cleandoc("""
            eval('''
            3 + 4
            ''')
            """)

            return_data = []
            async for result in AsyncCodeExecutor(codeblock, scope):
                return_data.append(result)

            self.assertEqual(len(return_data), 1, msg="Checking multi-line docstring eval returns")
            self.assertEqual(return_data[0], 7, msg="Checking eval return consistent")

            scope.clean()

        scope.update_globals({'add_numbers': self.add_numbers})

        return_data = []
        async for result in AsyncCodeExecutor("await add_numbers(10, 12)", scope):
            return_data.append(result)

        self.assertEqual(len(return_data), 1, msg="Checking await returns result")
        self.assertEqual(return_data[0], 22, msg="Checking await result consistent")
