.. currentmodule:: jishaku

jishaku as a cog
================

The jishaku cog contains commands for bot management, debugging and experimentation.

The conventional way to add the cog is by using the module as an extension:

.. code:: python3

    bot.load_extension('jishaku')

You can also write your own extension file to modify or supplement commands:

.. code:: python3

    from discord.ext import commands
    from jishaku import Jishaku

    class Debugging(Jishaku):
        ...

    def setup(bot: commands.Bot):
        bot.add_cog(Debugging(bot))

The ``jishaku`` command group has an owner check applied to it and all subcommands.
To change who can use jishaku, you must change how the owner is determined in your own Bot:

.. code:: python3

    class MyBot(commands.Bot):
        async def is_owner(self, user: discord.User):
            if something:  # Implement your own conditions here
                return True

            # Else fall back to the original
            return await super().is_owner(user)

Task system
-----------

Commands that execute arbitrary code are submitted to a command-task queue so they can be viewed and cancelled.
This includes the Python and shell commands.

Please note that this queue is specific to the cog instance.
If jishaku is reloaded, the command-task queue for the older instance will be lost, even if there are uncancelled command-tasks within it.
This will make it very difficult to cancel those tasks.

.. py:function:: jsk tasks

    Shows a list of the currently running command-tasks. This includes the index, command qualified name and time invoked.

.. py:function:: jsk cancel <index: int>

    Cancels the command-task at the provided index. If the index is -1, it will cancel the most recent still-running task.

    Note that this cancellation propagates up through the event call stack.
    Cancelling running evals or shell commands will likely cause them to give you back cancellation errors.

Python evaluation
-----------------

.. currentmodule:: jishaku.repl.compilation

Python execution and evaluation is facilitated by jishaku's :class:`AsyncCodeExecutor` backend.

Code can be passed in as either a single line or a full codeblock:

.. code:: md

    ?jsk py 3 + 4

    ?jsk py ```py
    return 3 + 4
    ```

Where any code supplied is a single expression, it is automatically returned.

Awaitables are returned as-is, without awaiting them.

Codeblocks passed support yielding. Yielding allows results to be received during execution:

.. code:: md

    ?jsk py ```py
    for x in range(5):
        yield x
    ```

Yielded results are treated the same as if they were returned.

When using the ``jsk py`` command, there are a set of contextual variables you can use to interact with Discord:

+----------------+-----------------------------------------------------------+
| ``_bot``       |  The :class:`discord.ext.commands.Bot` instance.          |
+----------------+-----------------------------------------------------------+
| ``_ctx``       |  The invoking :class:`discord.ext.commands.Context`.      |
+----------------+-----------------------------------------------------------+
| ``_message``   |  An alias for ``_ctx.message``.                           |
+----------------+                                                           |
| ``_msg``       |                                                           |
+----------------+-----------------------------------------------------------+
| ``_author``    |  An alias for ``_ctx.author``.                            |
+----------------+-----------------------------------------------------------+
| ``_channel``   |  An alias for ``_ctx.channel``.                           |
+----------------+-----------------------------------------------------------+
| ``_guild``     |  An alias for ``_ctx.guild``.                             |
+----------------+-----------------------------------------------------------+
| ``_find``      |  A shorthand for :func:`discord.utils.find`.              |
+----------------+-----------------------------------------------------------+
| ``_get``       |  A shorthand for :func:`discord.utils.get`.               |
+----------------+-----------------------------------------------------------+

Example:

.. code:: md

    ?jsk py ```py
    channel = _bot.get_channel(123456789012345678)

    await channel.send(_author.avatar_url_as(format='png'))
    ```

These variables are prefixed with underscores to try and reduce accidental shadowing when writing scripts in REPL.

If you don't want the underscores, you can set ``JISHAKU_NO_UNDERSCORE=true`` in your environment variables.

These variables are bound to the local scope and are actively cleaned from the scope on command exit,
so they should never persist between REPL sessions.


Commands
---------

.. py:function:: jsk [python|py] <argument: str>

    |tasked|

    Evaluates Python code, returning the results verbatim in its clearest representation.

    If None is received, nothing is sent.

    Where a string is sent, it will be shortened to fit in a single message. Mentions are not escaped.

    Empty strings will be sent as a ZWSP (``\u200b``).

    :class:`discord.File` instances will be uploaded.

    :class:`discord.Embed` instances will be sent as embeds.

    Any other instance is ``repr``'d and sent using the same rules as a string.

.. py:function:: jsk [python_inspect|pythoninspect|pyi] <argument: str>

    |tasked|

    Evaluates Python code, returning an inspection of the results.

    .. currentmodule:: jishaku.paginators

    If the inspection fits in a single message, it is sent as a paginator page,
    else it is sent as a :class:`PaginatorInterface`.


.. py:function:: jsk retain <toggle: bool>

    Toggles whether variables defined in REPL sessions are retained into future sessions. (OFF by default)

    .. currentmodule:: jishaku.repl.scope

    Toggling this on or off will destroy the current :class:`Scope`.

    Past variables can only be accessed if their session has already ended
    (you cannot concurrently share variables between running REPL sessions).


.. py:function:: jsk [shell|sh] <argument: str>

    |tasked|

    Evaluates code in the bash shell. ``stdout`` and ``stderr`` are read back asynchronously into the current channel.

    As with any code evaluation, use of this command may freeze your bot or damage your system. Choose what you enter carefully.


.. py:function:: jsk [load|reload] [extensions...]

    Loads, or reloads, a number of extensions. Extension names are delimited by spaces.

    This attempts to unload each extension, if possible, before loading it.

    If loading the extension fails, it will be reported with a traceback.

    Extensions can be specified en masse by typing e.g. ``cogs.*``.
    This searches for anything that looks like an extension in the folder and loads/reloads it.

    Brace expansion works as well, such as ``foo.bar.cogs.{baz,quux,garply}`` to reload ``foo.bar.cogs.baz``,
    ``foo.bar.cogs.quux``, and ``foo.bar.cogs.garply``.

    ``jsk reload ~`` will reload every extension the bot currently has loaded.


.. py:function:: jsk unload [extensions...]

    Unloads a number of extensions. Extension names are delimited by spaces.

    Matching rules are the same as ``jsk load``.

    Running ``jsk unload ~`` will unload every extension on your bot. This includes jishaku, which may leave you unable to maintain your bot
    until it is restarted. Use with care.

    If unloading the extension fails, it will be reported with a traceback.


.. py:function:: jsk su <member> <command: str>

    Runs a command as if it were ran by someone else.

    This allows you to test how your bot would react to other users, or perform administrative actions you may have not programmed yourself
    to be able to use by default.


.. py:function:: jsk in <channel> <command: str>

    Runs a command as if it were in a different channel.

    Because it matches a `TextChannel`, using this in a guild will only work for other channels in that guild.
    Cross-server remote commanding can be facilitated by DMing the bot instead.


.. py:function:: jsk sudo <command: str>

    Runs a command, ignoring any checks or cooldowns on the command.

    This forces the relevant callbacks to be triggered, and can be used to let you bypass any large cooldowns or conditions you have set.

.. py:function:: jsk debug <command: str>

    Runs a command using ``jsk python``-style timing and exception reporting.

    This allows you to invoke a broken command with this command to get the exception directly without having to read logs.

    When the command finishes, the time to run will be reported.

.. py:function:: jsk repeat <times: int> <command: str>

    |tasked|

    Repeats a command the specified amount of times.

    This works like a direct message invocation, so cooldowns *will* be honored.
    You can use ``jsk repeat . jsk sudo ..`` to bypass cooldowns on each invoke if need be.

    This command will wait for a previous invocation to finish before moving onto the next one.

.. py:function:: jsk cat <file: str>

    Reads out the data from a file, displaying it in a :class:`PaginatorInterface`.

    This command will attempt to work out the appropriate highlight.js language from the shebang (if present) or file extension,
    and will highlight the codeblock accordingly.

    If the file has an encoding hint, it will be honored when trying to read it.

    It is possible to specify a linespan by typing e.g. ``jsk cat file.py#L5-10``, which will only display lines 5 through 10 inclusive.

.. py:function:: jsk curl <url: str>

    Downloads a file from a URL, displaying the contents in a :class:`PaginatorInterface`.

    This command will attempt to work out the appropriate highlight.js language from the MIME type or URL
    and will highlight the codeblock accordingly.

    If the file has an encoding hint, it will be honored when trying to read it.

.. py:function:: jsk source <command_name: str>

    Shows the source for a command in a :class:`PaginatorInterface`.

    This is similar to doing ``jsk cat`` on the source file, limited to the line span of the command.
