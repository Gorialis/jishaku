# -*- coding: utf-8 -*-

"""
jishaku.repl.inspections
~~~~~~~~~~~~~~~~~~~~~~~~~

Inspections performable on Python objects.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import collections
import functools
import inspect
import os
import sys
import typing

INSPECTIONS: typing.List[
    typing.Tuple[
        str,
        typing.Callable[..., typing.Any]
    ]
] = []
MethodWrapperType = type((1).__le__)
WrapperDescriptorType = type(int.__le__)


T = typing.TypeVar('T')

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
    P = ParamSpec('P')
else:
    P = typing.ParamSpec('P')  # pylint: disable=no-member


def add_inspection(name: str) -> typing.Callable[
    [typing.Callable[P, T]],
    typing.Callable[P, T]
]:
    """
    Add a Jishaku object inspection
    """

    # create the real decorator
    def inspection_inner(func: typing.Callable[P, T]):
        """
        Jishaku inspection decorator
        """

        # pylint: disable=inconsistent-return-statements

        # create an encapsulated version of the inspection that swallows exceptions
        @functools.wraps(func)
        def encapsulated(*args: P.args, **kwargs: P.kwargs):
            try:
                return func(*args, **kwargs)
            except (TypeError, AttributeError, ValueError, OSError):
                return

        INSPECTIONS.append((name, encapsulated))
        return func
    return inspection_inner


def all_inspections(obj: typing.Any):
    """
    Generator to iterate all current Jishaku inspections.
    """

    for name, callback in INSPECTIONS:
        result = callback(obj)
        if result:
            yield name, result


def class_name(obj: typing.Any):
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
def type_inspection(obj: typing.Any):
    return type(obj).__name__


@add_inspection("Object ID")
def id_inspection(obj: typing.Any):
    return hex(id(obj))


@add_inspection("Length")
def len_inspection(obj: typing.Any):
    return len(obj)


@add_inspection("MRO")
def mro_inspection(obj: typing.Any):
    if not inspect.isclass(obj):
        return

    return ', '.join(class_name(x) for x in inspect.getmro(obj))


@add_inspection("Type MRO")
def type_mro_inspection(obj: typing.Any):
    obj_type = type(obj)
    if obj_type in (type, object):
        return

    return ', '.join(class_name(x) for x in inspect.getmro(obj_type))


@add_inspection("Subclasses")
def subclass_inspection(obj: typing.Any):
    if isinstance(obj, type) and hasattr(obj, "__subclasses__"):
        subclasses = type.__subclasses__(obj)
    else:
        return

    output = ', '.join(class_name(x) for x in subclasses[0:5])

    if len(subclasses) > 5:
        output += ', ...'

    return output


@add_inspection("Module Name")
def module_inspection(obj: typing.Any):
    return inspect.getmodule(obj).__name__  # type: ignore


@add_inspection("File Location")
def file_loc_inspection(obj: typing.Any):
    file_loc = inspect.getfile(obj)
    cwd = os.getcwd()
    if file_loc.startswith(cwd):
        file_loc = "." + file_loc[len(cwd):]
    return file_loc


@add_inspection("Line Span")
def line_span_inspection(obj: typing.Any):
    source_lines, source_offset = inspect.getsourcelines(obj)
    return f"{source_offset}-{source_offset + len(source_lines)}"


@add_inspection("Signature")
def sig_inspection(obj: typing.Any):
    return inspect.signature(obj)


@add_inspection("Content Types")
def content_type_inspection(obj: typing.Sized):
    if not isinstance(obj, (tuple, list, set)):
        return

    total = len(obj)  # type: ignore
    types = collections.Counter(type(x) for x in obj)  # type: ignore

    output = ', '.join(f'{x.__name__} ({y * 100 / total:.1f}\uFF05)' for x, y in types.most_common(3))
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
    '%': 'mod',
    '**': 'pow',
    '<<': 'lshift',
    '>>': 'rshift',
    '&': 'and',
    '^': 'xor',
    '|': 'or'
}


def check_not_slot(obj: typing.Any, attr: str):
    """
    Check that a given attribute isn't just an open slot for subclasses
    """

    if isinstance(getattr(obj, attr, None), MethodWrapperType):
        return not isinstance(getattr(type(obj), attr, None), WrapperDescriptorType)

    return not isinstance(getattr(obj, attr, None), WrapperDescriptorType)


@add_inspection("Operations")
def compat_operation_inspection(obj: typing.Any):
    this_dict = dir(obj)
    operations: typing.List[str] = []

    for operation, member in POSSIBLE_OPS.items():
        if f'__{member}__' in this_dict and check_not_slot(obj, f'__{member}__'):
            operations.append(operation)
        elif f'__r{member}__' in this_dict and check_not_slot(obj, f'r__{member}__'):
            operations.append(operation)

        if f'__i{member}__' in this_dict and check_not_slot(obj, f'i__{member}__'):
            operations.append(f'{operation}=')

    return ' '.join(operations)
