.. currentmodule:: jishaku

jishaku as a cog
================

Custom cogs and the Feature framework
--------------------------------------

The jishaku cog contains commands for bot management, debugging and experimentation.

The conventional way to add the cog is by using the module as an extension:

.. code:: python3

    bot.load_extension('jishaku')

You could also create your own extension to load the ``Jishaku`` cog, but this is not recommended:

.. code:: python3

    from jishaku.cog import Jishaku

    def setup(bot: commands.Bot):
        # I don't recommend doing this!
        bot.add_cog(Jishaku(bot=bot))

If you wish to change or add to the functionality on jishaku for your specific bot, you must use the Features framework to create a new cog.

The ``Jishaku`` cog is composited from multiple Features that implement various parts of its functionality.
When the cog is instantiated, the inherited Features are used to compile the final command tree.

.. image:: /images/features.png

Here is an example of a simple custom cog using this setup:

.. code:: python3

    from discord.ext import commands

    from jishaku.features.python import PythonFeature
    from jishaku.features.root_command import RootCommand

    class CustomDebugCog(PythonFeature, RootCommand):
        pass

    def setup(bot: commands.Bot):
        bot.add_cog(CustomDebugCog(bot=bot))

This example would give you a cog that includes the ``jsk`` command, the core task system, and the Python commands, but nothing else.

Using this system, you can selectively include or exclude features you want on your custom Cogs.

``STANDARD_FEATURES`` in ``jishaku.cog`` holds all the features that an installation of jishaku is guaranteed to have by default.
Thus, you can make a cog without any optional features like so:

.. code:: python3

    from discord.ext import commands

    from jishaku.cog import STANDARD_FEATURES

    class CustomDebugCog(*STANDARD_FEATURES):
        pass

    def setup(bot: commands.Bot):
        bot.add_cog(CustomDebugCog(bot=bot))

``OPTIONAL_FEATURES``, by contrast, contains Features detected to be supported in this environment.
The content of it may vary depending on what extras have been installed, or what platform jishaku is running on.

To use these features as well, simply add them to your cog:

.. code:: python3

    from discord.ext import commands

    from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES

    class CustomDebugCog(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
        pass

    def setup(bot: commands.Bot):
        bot.add_cog(CustomDebugCog(bot=bot))

This will give you an almost identical cog to the standard Jishaku.

Adding or changing commands
----------------------------

If you want to add or change commands in your custom cog, you can use ``Feature.Command``.

This operates in a similar manner to ``commands.command``, but it allows command cross-referencing between different Features, and guarantees individual instances of jishaku cogs will have unique states.

.. code:: python3

    from jishaku.features.baseclass import Feature

    class CustomDebugCog(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
        @Feature.Command(parent="jsk", name="foobar")
        async def jsk_foobar(self, ctx: commands.Context):
            await ctx.send("Hello there!")

The ``parent`` argument refers to what command parents this one, and works across Features.
The name used in it is the **function name of the callback for the command**, not the command's name itself, so please keep this in mind.

If you need to check what the name of a command you want to parent against is, you can use ``jsk source jsk <whatever>``.

Commands that have children when the cog is instantiated will be automatically turned into ``Group`` s, and this applies for subcommands of subcommands and etc.

If you want to override existing commands, the process is moreorless the same:

.. code:: python3

    class CustomDebugCog(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
        @Feature.Command(parent="jsk", name="debug")
        async def jsk_debug(self, ctx: commands.Context):
            await ctx.send("Not so debuggy any more!")

Like standard inheritance, this requires the **function name to be the same to work properly**, so keep this in mind.

You can even override the jishaku base command using this method:

.. code:: python3

    class CustomDebugCog(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
        @Feature.Command(name="jishaku", aliases=["jsk"], invoke_without_command=True, ignore_extra=False)
        async def jsk(self, ctx: commands.Context):
            await ctx.send("I'm walking on a Star!")

Changing who can use jishaku
-----------------------------

The ``jishaku`` command group has an owner check applied to it and all subcommands.
To change who can use jishaku, you must change how the owner is determined in your own Bot:

.. code:: python3

    class MyBot(commands.Bot):
        async def is_owner(self, user: discord.User):
            if something:  # Implement your own conditions here
                return True

            # Else fall back to the original
            return await super().is_owner(user)

This is the **sole** supported method of changing who can use jishaku.

jishaku is a powerful tool - giving people access to it is equivalent to giving them direct access to your computer - so you should make serious consideration for whether you should be overriding who can use it at all.

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
so they don't persist between REPL sessions.

If you want to change this behavior, you can set ``JISHAKU_RETAIN=true``, or,
use the ``jsk retain on`` and ``jsk retain off`` commands to toggle variable retention.


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


.. py:function:: jsk [disassemble|dis] <argument: str>

    Compiles Python code in an asynchronous context, and returns the disassembly.

    This operates in a similar manner to :func:`dis.dis`, but in a more accessible form, as it is in an implicit async context and doesn't send to stdout.

    .. currentmodule:: jishaku.paginators

    The output is always sent as a :class:`PaginatorInterface`.


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

    If no output is produced by the command for 120 seconds, a :class:`asyncio.TimeoutException` will be raised and the shell process will be terminated.


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


.. py:function:: jsk exec [member_and_or_channel...] <command: str>

    Runs a command as if it were ran by someone else and/or in a different channel.

    This allows you to test how your bot would react to other users, or perform administrative actions you may have not programmed yourself
    to be able to use by default.

    You can provide a channel to redirect command location, a user to redirect command origin, or both.

    If `exec!` is used instead of `exec`, the command will bypass all checks and cooldowns, directly triggering the callback.

.. py:function:: jsk permtrace <channel> [targets...]

    Emulates Discord's permission calculation system to create a breakdown of where certain permissions for a member come from.

    Targets can either be a member, or a list of roles (to emulate a member with those roles).
    The command will take into account guild permissions and the overwrites for the roles (and member, if applicable) to produce the resulting effective permissions.

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

.. py:function:: jsk rtt

    Calculates the round trip time between your bot and the API, using message sends and edits.
    The latency for each pass will be shown, as well as an average and standard deviation.

    This command will also output the websocket latency.
