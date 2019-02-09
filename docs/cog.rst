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

.. py:function:: jsk cancel <index>

    Cancels the command-task at the provided index. If the index is -1, it will cancel the most recent still-running task.

    Note that this cancellation propagates up through the event call stack.
    Cancelling running evals or shell commands will likely cause them to give you back cancellation errors.

Python evaluation
-----------------

.. currentmodule:: jishaku.repl.compilation

Python execution and evaluation is facilitated by jishaku's :class:`AsyncCodeExecutor` backend.

Code can be passed in as either a single line or a full codeblock:

.. code::

    ?jsk py 3 + 4

    ?jsk py ```py
    return 3 + 4
    ```

Where any code supplied is a single expression, it is automatically returned.

Awaitables are returned as-is, without awaiting them.

Codeblocks passed support yielding. Yielding allows results to be received during execution:

.. code::

    ?jsk py ```py
    for x in range(5):
        yield x
    ```

Yielded results are treated the same as if they were returned.

Commands
~~~~~~~~

.. py:function:: jsk [python|py] <argument: str>

    Evaluates Python code, returning the results verbatim in its clearest representation.

    If None is received, nothing is sent.

    Where a string is sent, it will be shortened to fit in a single message. Mentions are not escaped.

    Empty strings will be sent as a ZWSP (``\u200b``).

    :class:`discord.File` instances will be uploaded.

    :class:`discord.Embed` instances will be sent as embeds.

    Any other instance is ``repr``'d and sent using the same rules as a string.

.. py:function:: jsk [python_inspect|pythoninspect|pyi] <argument: str>

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

    Evaluates code in the bash shell. ``stdout`` and ``stderr`` are read back asynchronously into the current channel.

    As with any code evaluation, use of this command may freeze your bot or damage your system. Choose what you enter carefully.


.. py:function:: jsk [load|reload] [extensions...]

    Loads, or reloads, a number of extensions. Extension names are delimited by spaces.

    This attempts to unload each extension, if possible, before loading it.

    If loading the extension fails, it will be reported with a traceback.

    Extensions can be specified en masse by typing e.g. ``cogs.*``.
    This searches for anything that looks like an extension in the folder and loads/reloads it.

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


.. py:function:: jsk sudo <command: str>

    Runs a command, ignoring any checks or cooldowns on the command.

    This forces the relevant callbacks to be triggered, and can be used to let you bypass any large cooldowns or conditions you have set.
