# -*- coding: utf-8 -*-

"""
jishaku.repl.scope
~~~~~~~~~~~~~~~~~~

The Scope class and functions relating to it.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import inspect
import typing


class Scope:
    """
    Class that represents a global and local scope for both scope inspection and creation.

    Many REPL functions expect or return this class.

    .. code:: python3

        scope = Scope()  # an empty Scope

        scope = Scope(globals(), locals())  # a Scope imitating the current, real scope.

        scope = Scope({'a': 3})  # a Scope with a pre-existing global scope key, and an empty local scope.
    """

    __slots__ = ('globals', 'locals')

    def __init__(self, globals_: dict = None, locals_: dict = None):
        self.globals: dict = globals_ or {}
        self.locals: dict = locals_ or {}

    def clean(self):
        """
        Clears out keys starting with an underscore.

        This reduces cross-eval pollution by removing private variables.

        Returns
        -------
        Scope
            The updated scope (self).
        """

        for key in tuple(self.globals.keys()):
            if key.startswith('_') and not key.startswith('__'):
                del self.globals[key]

        for key in tuple(self.locals.keys()):
            if key.startswith('_') and not key.startswith('__'):
                del self.locals[key]

        return self

    def update(self, other):
        """
        Updates this scope with the content of another scope.

        Arguments
        ---------
        other: a :class:`Scope` instance.

        Returns
        -------
        Scope
            The updated scope (self).
        """
        self.globals.update(other.globals)
        self.locals.update(other.locals)
        return self

    def update_globals(self, other: dict):
        """
        Updates this scope's globals with a dict.

        Arguments
        ---------
        other: a :class:`dict` to be merged into this scope.

        Returns
        -------
        Scope
            The updated scope (self).
        """

        self.globals.update(other)
        return self

    def update_locals(self, other: dict):
        """
        Updates this scope's locals with a dict.

        Arguments
        ---------
        other: a :class:`dict` to be merged into this scope.

        Returns
        -------
        Scope
            The updated scope (self).
        """

        self.locals.update(other)
        return self


def get_parent_scope_from_var(name, global_ok=False, skip_frames=0) -> typing.Optional[Scope]:
    """
    Iterates up the frame stack looking for a frame-scope containing the given variable name.

    Returns
    --------
    Optional[Scope]
        The relevant :class:`Scope` or None
    """

    stack = inspect.stack()
    try:
        for frame_info in stack[skip_frames + 1:]:
            frame = None

            try:
                frame = frame_info.frame

                if name in frame.f_locals or (global_ok and name in frame.f_globals):
                    return Scope(globals_=frame.f_globals, locals_=frame.f_locals)
            finally:
                del frame
    finally:
        del stack

    return None


def get_parent_var(name, global_ok=False, default=None, skip_frames=0):
    """
    Directly gets a variable from a parent frame-scope.

    Returns
    --------
    Any
        The content of the variable found by the given name, or None.
    """

    scope = get_parent_scope_from_var(name, global_ok=global_ok, skip_frames=skip_frames + 1)

    if not scope:
        return default

    if name in scope.locals:
        return scope.locals.get(name, default)

    return scope.globals.get(name, default)
