jishaku
=======

jishaku is a debugging and experimenting cog for Discord bots using ``discord.py@rewrite``.

It is locked to Python 3.6 and requirements will shift as new ``discord.py`` and Python versions release.
This repo primarily exists for the purpose of example and usage in other bot projects.

Installing
----------

This cog can be installed through the following command:

.. code:: sh

    python3 -m pip install -U git+https://github.com/Gorialis/jishaku@master#egg=jishaku

It can be used in bots directly using

.. code:: python3

    bot.load_extension("jishaku")

Functionality
-------------

Extension loading/unloading
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Jishaku contains 3 commands for loading and unloading extensions:

- ``[jishaku|jsk] load [exts...]``
- ``[jishaku|jsk] unload [exts...]``
- ``[jishaku|jsk] reload [exts...]``

These commands do as described, with ``reload`` unloading and loading cogs again for quick reloads.
``[exts...]`` are a set of extension names separated by spaces, such as ``cogs.one cogs.two cogs.three``.

Python REPL
~~~~~~~~~~~

Jishaku can evaluate Python code with ``[jishaku|jsk] [python|py] <codeline|codeblock>``.

By default eval-mode is used, allowing you to type statements like ``3+4`` or ``_ctx.author.name`` to return their result.
Eval-mode supports async syntax, so you can do evaluations like ``await coro()`` or ``[m async for m in _ctx.history()]``.

Exec-mode will be used whenever eval-mode fails. In this mode, you can use control flow and ``return`` manually.

Variables available in both eval and exec modes are:

- ``_bot``: Represents the current ``commands.Bot`` instance.
- ``_ctx``: Represents the current ``commands.Context``.
- ``_message``: Shorthand for ``_ctx.message``
- ``_msg``: Shorthand for ``_ctx.message``
- ``_guild``: Shorthand for ``_ctx.guild``
- ``_channel``: Shorthand for ``_ctx.channel``
- ``_author``: Shorthand for ``_ctx.message.author``

``_bot`` is globally available, but all other REPL variables are local (that is, editing or overwriting them won't affect other current repl sessions)

Shell Interaction
~~~~~~~~~~~~~~~~~

Jishaku can interact with CLI programs with ``[jishaku|jsk] sh <codeline|codeblock>``.

This opens a subprocess, meaning you can run standard shell commands like ``git pull`` or such, but cannot use specific shell syntax like piping or envvars.
