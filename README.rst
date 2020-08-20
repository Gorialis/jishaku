jishaku
=======

.. |py| image:: https://img.shields.io/pypi/pyversions/jishaku.svg

.. |license| image:: https://img.shields.io/pypi/l/jishaku.svg
  :target: https://github.com/Gorialis/jishaku/blob/master/LICENSE

.. |status| image:: https://img.shields.io/pypi/status/jishaku.svg
  :target: https://pypi.python.org/pypi/jishaku

.. |travis| image:: https://img.shields.io/travis/Gorialis/jishaku/master.svg?label=TravisCI
  :target: https://travis-ci.org/Gorialis/jishaku

.. |circle| image:: https://img.shields.io/circleci/project/github/Gorialis/jishaku/master.svg?label=CircleCI
  :target: https://circleci.com/gh/Gorialis/jishaku

.. |appveyor| image:: https://img.shields.io/appveyor/ci/Gorialis/jishaku.svg?label=AppVeyorCI
  :target: https://ci.appveyor.com/project/Gorialis/jishaku

.. |issues| image:: https://img.shields.io/github/issues/Gorialis/jishaku.svg?colorB=3333ff
  :target: https://github.com/Gorialis/jishaku/issues

.. |commit| image:: https://img.shields.io/github/commit-activity/w/Gorialis/jishaku.svg
  :target: https://github.com/Gorialis/jishaku/commits

|py| |license| |status|
|travis| |circle| |appveyor|
|issues| |commit|

jishaku is a debugging and experimenting cog for Discord bots using ``discord.py``.

It is locked to Python 3.7+ and requirements will shift as new ``discord.py`` and Python versions release.
This repo primarily exists for the purpose of example and usage in other bot projects.

Some documentation is available on `readthedocs <https://jishaku.readthedocs.io/en/latest/>`__.
If in doubt, all commands have docstrings visible from the help command.

Installing
-----------

This cog can be installed through the following command:

.. code:: sh

    python3 -m pip install -U jishaku

Or the development version:

+-------------------------------------------------------------------------------------------+
| From GitHub:                                                                              |
|                                                                                           |
| .. code:: sh                                                                              |
|                                                                                           |
|     python3 -m pip install -U "jishaku @ git+https://github.com/Gorialis/jishaku@master"  |
|                                                                                           |
| From GitLab:                                                                              |
|                                                                                           |
| .. code:: sh                                                                              |
|                                                                                           |
|     python3 -m pip install -U "jishaku @ git+https://gitlab.com/Gorialis/jishaku@master"  |
|                                                                                           |
+-------------------------------------------------------------------------------------------+

It can be used in bots directly using

.. code:: python3

    bot.load_extension("jishaku")

Functionality
-------------

Extension loading/unloading
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Jishaku contains 3 commands for loading and unloading extensions:

- ``[jishaku|jsk] load [exts...]``
- ``[jishaku|jsk] reload [exts...]``
- ``[jishaku|jsk] unload [exts...]``

These commands do as described, with ``reload`` unloading and loading cogs again for quick reloads.
``[exts...]`` are a set of extension names separated by spaces, such as ``cogs.one cogs.two cogs.three``.
``reload`` is actually an alias of ``load``, extensions are automatically reloaded based on their presence.

Reloading jishaku itself can be done conventionally with ``[jishaku|jsk] reload jishaku``.

Task queue
~~~~~~~~~~

Some actions jishaku can do may take a long time, and could be invoked incorrectly or by accident.
As such, jishaku implements a command queue that long-lasting commands are submitted to.

- ``[jishaku|jsk] tasks``
- ``[jishaku|jsk] cancel <id>``

``tasks`` shows which tasks are currently running, for what commands. You can use this to figure out which task you need to cancel.

``cancel`` cancels a task by a given ID. It will accept a numeric ID as shown in ``tasks``. Supplying ``-1`` will make it cancel the last task submitted.

Python REPL
~~~~~~~~~~~

Jishaku can evaluate Python code with ``[jishaku|jsk] [python|py] <codeline|codeblock>``.

Evaluation-like REPL is supported, allowing you to type statements like ``3+4`` or ``_ctx.author.name`` to return their result.
This supports async syntax, so you can do evaluations like ``await coro()`` or ``[m async for m in _ctx.history()]``.

In large blocks, the last standalone expression will be returned if not in a control flow block.

Variables available in REPL are:

- ``_bot``: Represents the current ``commands.Bot`` instance.
- ``_ctx``: Represents the current ``commands.Context``.
- ``_message``: Shorthand for ``_ctx.message``
- ``_msg``: Shorthand for ``_ctx.message``
- ``_guild``: Shorthand for ``_ctx.guild``
- ``_channel``: Shorthand for ``_ctx.channel``
- ``_author``: Shorthand for ``_ctx.message.author``

These variables are local and cleared between sessions, so they will not persist into other sessions.

The underscore prefix is to help reduce accidental shadowing. If you don't want your variables to be prefixed, set ``JISHAKU_NO_UNDERSCORE=true`` in your environment variables.

By default, variables are not shared at all between REPL contexts. You can use ``[jishaku|jsk] retain on`` to try and preserve locals between sessions.

Yielding inside of a codeblock allows you to return intermediate data as your code runs. Any objects yielded will be treated as if they were returned, without terminating execution.

(Note that as yielding creates an asynchronous generator, you can no longer return and must yield for **all** results you feed back.)

An alternate command is available, ``[jishaku|jsk] [python_inspect|pyi] <codeline|codeblock>``.

This command performs identically as the standard REPL, but inspects yielded results instead of just formatting them.

Shell Interaction
~~~~~~~~~~~~~~~~~

Jishaku can interact with CLI programs with ``[jishaku|jsk] sh <codeline|codeblock>``.

On Windows, this acts similar to Command Prompt.

On Linux, your shell is automatically determined from ``$SHELL``, or set to bash if no such environment variable exists.

For bots maintained using the git version control system, a shortcut command ``[jishaku|jsk] git <codeline>`` is available.

This simply invokes the sh command, but prefixes with git to make running git commands easier, such as ``jsk git pull``.

Command Invocation
~~~~~~~~~~~~~~~~~~

Jishaku can invoke other commands on your bot in special modes:

- ``[jishaku|jsk] sudo <command string>``
- ``[jishaku|jsk] debug <command string>``
- ``[jishaku|jsk] repeat <times> <command string>``
- ``[jishaku|jsk] su <member> <command string>``
- ``[jishaku|jsk] in <channel> <command string>``

``sudo`` invokes a command bypassing all checks and cooldowns. This may also invoke parent group callbacks, depending on how the command is defined.
For example, ``jsk sudo foo`` will invoke ``foo`` regardless of if checks or cooldowns fail.

``debug`` invokes a command normally, but as if it were in a Jishaku evaluation context with a timer.
This means if an exception occurs, it will be direct messaged to you like as in ``jishaku python``.

When execution finishes, the time taken to complete execution will be sent as a message.

``repeat`` invokes a command many times in a row. It acts the same as a direct message invocation, so it *will* obey cooldowns if commands have them.
As this command may take a long time, it is submitted to the task queue so it can be cancelled.

``su`` invokes a command as if it was invoked directly by another member.
This allows you to effectively impersonate another account to your own bot, such that you can perform actions on their behalf or test command behavior.

For example, ``jsk su @Clyde#0001 foo`` will invoke ``foo`` as if it was used directly by ``@Clyde#0001``.
This command won't work on users that the bot cannot see.

Trying to use this command with a user that is not in the current guild (if applicable) will work, but may cause weird side effects, so it is recommended to restrict usage to available members.

``in`` invokes a command as if it was invoked in another channel.
In guilds, this only works in channels of the same guild, but can work across guilds if ``in`` is used in a DM.
