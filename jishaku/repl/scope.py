# -*- coding: utf-8 -*-

"""
jishaku.repl.scope
~~~~~~~~~~~~~~~~~~

The Scope class and functions relating to it.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""


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

    def clear_intersection(self, other_dict):
        """
        Clears out locals and globals from this scope where the key-value pair matches
        with other_dict.

        This allows cleanup of temporary variables that may have washed up into this
        Scope.

        Parameters
        -----------
        other_dict: :class:`dict`
            The dictionary to be used to determine scope clearance.

            If a key from this dict matches an entry in the globals or locals of this scope,
            and the value is identical, it is removed from the scope.

        Returns
        -------
        Scope
            The updated scope (self).
        """

        for key, value in other_dict.items():
            if key in self.globals and self.globals[key] is value:
                del self.globals[key]
            if key in self.locals and self.locals[key] is value:
                del self.locals[key]

        return self

    def update(self, other):
        """
        Updates this scope with the content of another scope.

        Parameters
        ---------
        other: :class:`Scope`
            The scope to overlay onto this one.

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

        Parameters
        -----------
        other: :class:`dict`
            The dictionary to be merged into this scope.

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

        Parameters
        -----------
        other: :class:`dict`
            The dictionary to be merged into this scope.

        Returns
        -------
        Scope
            The updated scope (self).
        """

        self.locals.update(other)
        return self
