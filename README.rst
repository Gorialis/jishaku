jishaku
=======

.. |py| image:: https://img.shields.io/pypi/pyversions/jishaku.svg

.. |license| image:: https://img.shields.io/pypi/l/jishaku.svg
  :target: https://github.com/Gorialis/jishaku/blob/master/LICENSE

.. |travis| image:: https://img.shields.io/travis/Gorialis/jishaku/master.svg?label=TravisCI
  :target: https://travis-ci.org/Gorialis/jishaku

.. |circle| image:: https://img.shields.io/circleci/project/github/Gorialis/jishaku/master.svg?label=CircleCI
  :target: https://circleci.com/gh/Gorialis/jishaku

.. |issues| image:: https://img.shields.io/github/issues/Gorialis/jishaku.svg?colorB=3333ff
  :target: https://github.com/Gorialis/jishaku/issues

.. |commit| image:: https://img.shields.io/github/commit-activity/w/Gorialis/jishaku.svg
  :target: https://github.com/Gorialis/jishaku/commits

.. |status| image:: https://img.shields.io/pypi/status/jishaku.svg
  :target: https://pypi.python.org/pypi/jishaku

|py| |license| |travis| |circle| |issues| |commit| |status|

jishaku is a debugging and experimenting cog for Discord bots using ``discord.py@rewrite``.

It is locked to Python 3.6 and requirements will shift as new ``discord.py`` and Python versions release.
This repo primarily exists for the purpose of example and usage in other bot projects.

Installing
----------

+-------------------------------------------------------------------------------------------------------+
| **This cog does not work without discord.py@rewrite**                                                 |
|                                                                                                       |
| **Not having it installed properly will make the cog fail to install**                                |
|                                                                                                       |
| Use the following to install ``discord.py@rewrite`` on the latest version:                            |
|                                                                                                       |
| .. code:: sh                                                                                          |
|                                                                                                       |
|     python3 -m pip install -U git+https://github.com/Rapptz/discord.py@rewrite#egg=discord.py[voice]  |
+-------------------------------------------------------------------------------------------------------+


This cog can be installed through the following command:

.. code:: sh

    python3 -m pip install -U jishaku

Or the development version:

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

Jishaku can reload itself using ``[jishaku|jsk] selfreload``.

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

Yielding inside of an eval codeblock allows you to return intermediate data as your code runs. Any objects yielded will be treated as if they were returned, without terminating execution.

(Note that as yielding creates an asynchronous generator, you can no longer return and must yield for **all** results you feed back.)

An alternate command is available, ``[jishaku|jsk] [python_what|pyw] <codeline|codeblock>``.

This command performs identically as the standard eval, but inspects yielded results instead of just formatting them.

Shell Interaction
~~~~~~~~~~~~~~~~~

Jishaku can interact with CLI programs with ``[jishaku|jsk] sh <codeline|codeblock>``.

This opens a bash subprocess, meaning you can run standard shell commands or bash syntax.

Usually most distributions have bash installed in some capacity, but inside bot containers running minimalist distros such as Alpine, it may not be available.
In this case you will need to install bash in order to use the sh command:

.. code:: sh

    apk add --no-cache bash

For bots maintained using the git version control system, a shortcut command ``[jishaku|jsk] git <codeline>`` is available.

This simply invokes the sh command, but prefixes with git to make running git commands easier, such as ``jsk git pull``.
