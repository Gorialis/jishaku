# -*- coding: utf-8 -*-

"""
jishaku.repl.inspections
~~~~~~~~~~~~~~~~~~~~~~~~~

Inspections performable on Python objects.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import collections
import functools
import inspect
import os

INSPECTIONS = []


def add_inspection(name):
    """
    Add a Jishaku object inspection
    """

    # create the real decorator
    def inspection_inner(func):
        """
        Jishaku inspection decorator
        """

        # pylint: disable=inconsistent-return-statements

        # create an encapsulated version of the inspection that swallows exceptions
        @functools.wraps(func)
        def encapsulated(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (TypeError, AttributeError, ValueError, OSError):
                return

        INSPECTIONS.append((name, encapsulated))
        return func
    return inspection_inner


def all_inspections(obj):
    """
    Generator to iterate all current Jishaku inspections.
    """

    for name, callback in INSPECTIONS:
        result = callback(obj)
        if result:
            yield name, result


def class_name(obj):
    """
    Get the name of an object, including the module name if available.
    """

    name = obj.__name__
    module = getattr(obj, '__module__')

    if module:
        name = f'{module}.{name}'
    return name


# pylint: disable=missing-docstring
# pylint: disable=inconsistent-return-statements


@add_inspection("Type")
def type_inspection(obj):
    return type(obj).__name__


@add_inspection("Object ID")
def id_inspection(obj):
    return hex(id(obj))


@add_inspection("Length")
def len_inspection(obj):
    return len(obj)


@add_inspection("MRO")
def mro_inspection(obj):
    if not inspect.isclass(obj):
        return

    return ', '.join(class_name(x) for x in inspect.getmro(obj))


@add_inspection("Type MRO")
def type_mro_inspection(obj):
    obj_type = type(obj)
    if obj_type in (type, object):
        return

    return ', '.join(class_name(x) for x in inspect.getmro(obj_type))


@add_inspection("Subclasses")
def subclass_inspection(obj):
    if not hasattr(obj, "__subclasses__"):
        return

    if isinstance(obj, type):
        subclasses = type.__subclasses__(obj)
    else:
        subclasses = obj.__subclasses__()

    output = ', '.join(class_name(x) for x in subclasses[0:5])

    if len(subclasses) > 5:
        output += ', ...'

    return output


@add_inspection("Module Name")
def module_inspection(obj):
    return inspect.getmodule(obj).__name__


@add_inspection("File Location")
def file_loc_inspection(obj):
    file_loc = inspect.getfile(obj)
    cwd = os.getcwd()
    if file_loc.startswith(cwd):
        file_loc = "." + file_loc[len(cwd):]
    return file_loc


@add_inspection("Line Span")
def line_span_inspection(obj):
    source_lines, source_offset = inspect.getsourcelines(obj)
    return f"{source_offset}-{source_offset + len(source_lines)}"


@add_inspection("Signature")
def sig_inspection(obj):
    return inspect.signature(obj)


@add_inspection("Content Types")
def content_type_inspection(obj):
    if not isinstance(obj, (tuple, list, set)):
        return

    total = len(obj)
    types = collections.Counter(type(x) for x in obj)

    output = ', '.join(f'{x.__name__} ({y*100/total:.1f}\uFF05)' for x, y in types.most_common(3))
    if len(types) > 3:
        output += ', ...'

    return output


POSSIBLE_OPS = {
    '<': 'lt',
    '<=': 'le',
    '==': 'eq',
    '!=': 'ne',
    '>': 'gt',
    '>=': 'ge',
    '+': 'add',
    '-': 'sub',
    '*': 'mul',
    '@': 'matmul',
    '/': 'truediv',
    '//': 'floordiv',
    '\uFF05': 'mod',  # fake percent to avoid prolog comment
    '**': 'pow',
    '<<': 'lshift',
    '>>': 'rshift',
    '&': 'and',
    '^': 'xor',
    '|': 'or'
}


@add_inspection("Operations")
def compat_operation_inspection(obj):
    obj_dict = dir(obj)
    operations = []

    for operation, member in POSSIBLE_OPS.items():
        if f'__{member}__' in obj_dict or f'__r{member}__' in obj_dict:
            operations.append(operation)
        if f'__i{member}__' in obj_dict:
            operations.append(f'{operation}=')

    return ' '.join(operations)
