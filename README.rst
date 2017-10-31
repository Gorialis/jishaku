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

Commands
--------

The two primary (and only) commands as of current are ``jsk py`` and ``jsk sh``

``py`` evaluates and executes Python statements, supporting ``await`` and async list comprehension.

``sh`` opens subprocesses running other programs or CLI commands.
