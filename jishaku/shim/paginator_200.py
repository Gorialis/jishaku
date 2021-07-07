# -*- coding: utf-8 -*-

"""
jishaku.paginators (shim for discord.py 2.0.0)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Paginator-related tools and interfaces for Jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio

import discord
from discord import ui
from discord.ext import commands

from jishaku.shim.paginator_base import EMOJI_DEFAULT


class PaginatorInterface(ui.View):  # pylint: disable=too-many-instance-attributes
    """
    A message and reaction based interface for paginators.

    This allows users to interactively navigate the pages of a Paginator, and supports live output.

    An example of how to use this with a standard Paginator:

    .. code:: python3

        from discord.ext import commands

        from jishaku.paginators import PaginatorInterface

        # In a command somewhere...
            # Paginators need to have a reduced max_size to accommodate the extra text added by the interface.
            paginator = commands.Paginator(max_size=1900)

            # Populate the paginator with some information
            for line in range(100):
                paginator.add_line(f"Line {line + 1}")

            # Create and send the interface.
            # The 'owner' field determines who can interact with this interface. If it's None, anyone can use it.
            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            await interface.send_to(ctx)

            # send_to creates a task and returns control flow.
            # It will raise if the interface can't be created, e.g., if there's no reaction permission in the channel.
            # Once the interface has been sent, line additions have to be done asynchronously, so the interface can be updated.
            await interface.add_line("My, the Earth sure is full of things!")

            # You can also check if it's closed using the 'closed' property.
            if not interface.closed:
                await interface.add_line("I'm still here!")
    """

    def __init__(self, bot: commands.Bot, paginator: commands.Paginator, **kwargs):
        if not isinstance(paginator, commands.Paginator):
            raise TypeError('paginator must be a commands.Paginator instance')

        self._display_page = 0

        self.bot = bot

        self.message = None
        self.paginator = paginator

        self.owner = kwargs.pop('owner', None)
        self.emojis = kwargs.pop('emoji', EMOJI_DEFAULT)
        self.timeout = kwargs.pop('timeout', 7200)
        self.delete_message = kwargs.pop('delete_message', False)

        self.sent_page_reactions = False

        self.task: asyncio.Task = None
        self.send_lock: asyncio.Event = asyncio.Event()

        self.close_exception: Exception = None

        if self.page_size > self.max_page_size:
            raise ValueError(
                f'Paginator passed has too large of a page size for this interface. '
                f'({self.page_size} > {self.max_page_size})'
            )

        super().__init__(timeout=self.timeout)

    @property
    def pages(self):
        """
        Returns the paginator's pages without prematurely closing the active page.
        """
        # protected access has to be permitted here to not close the paginator's pages

        # pylint: disable=protected-access
        paginator_pages = list(self.paginator._pages)
        if len(self.paginator._current_page) > 1:
            paginator_pages.append('\n'.join(self.paginator._current_page) + '\n' + (self.paginator.suffix or ''))
        # pylint: enable=protected-access

        return paginator_pages

    @property
    def page_count(self):
        """
        Returns the page count of the internal paginator.
        """

        return len(self.pages)

    @property
    def display_page(self):
        """
        Returns the current page the paginator interface is on.
        """

        self._display_page = max(0, min(self.page_count - 1, self._display_page))
        return self._display_page

    @display_page.setter
    def display_page(self, value):
        """
        Sets the current page the paginator is on. Automatically pushes values inbounds.
        """

        self._display_page = max(0, min(self.page_count - 1, value))

    max_page_size = 2000

    @property
    def page_size(self) -> int:
        """
        A property that returns how large a page is, calculated from the paginator properties.

        If this exceeds `max_page_size`, an exception is raised upon instantiation.
        """
        page_count = self.page_count
        return self.paginator.max_size + len(f'\nPage {page_count}/{page_count}')

    @property
    def send_kwargs(self) -> dict:
        """
        A property that returns the kwargs forwarded to send/edit when updating the page.

        As this must be compatible with both `discord.TextChannel.send` and `discord.Message.edit`,
        it should be a dict containing 'content', 'embed' or both.
        """

        content = self.pages[self.display_page]
        return {'content': content, 'view': self}

    def update_view(self):
        """
        Updates view buttons to correspond to current interface state.
        This is used internally.
        """

        self.button_start.label = f"1 \u200b {self.emojis.start}"
        self.button_previous.label = self.emojis.back
        self.button_current.label = str(self.display_page + 1)
        self.button_next.label = self.emojis.forward
        self.button_last.label = f"{self.emojis.end} \u200b {self.page_count}"
        self.button_close.label = f"{self.emojis.close} \u200b Close paginator"

    async def add_line(self, *args, **kwargs):
        """
        A proxy function that allows this PaginatorInterface to remain locked to the last page
        if it is already on it.
        """

        display_page = self.display_page
        page_count = self.page_count

        self.paginator.add_line(*args, **kwargs)

        new_page_count = self.page_count

        if display_page + 1 == page_count:
            # To keep position fixed on the end, update position to new last page and update message.
            self._display_page = new_page_count

        # Unconditionally set send lock to try and guarantee page updates on unfocused pages
        self.send_lock.set()

    async def send_to(self, destination: discord.abc.Messageable):
        """
        Sends a message to the given destination with this interface.

        This automatically creates the response task for you.
        """

        self.message = await destination.send(**self.send_kwargs)

        self.send_lock.set()

        if self.task:
            self.task.cancel()

        self.task = self.bot.loop.create_task(self.wait_loop())

        return self

    @property
    def closed(self):
        """
        Is this interface closed?
        """

        if not self.task:
            return False
        return self.task.done()

    async def send_lock_delayed(self):
        """
        A coroutine that returns 1 second after the send lock has been released
        This helps reduce release spam that hits rate limits quickly
        """

        gathered = await self.send_lock.wait()
        self.send_lock.clear()
        await asyncio.sleep(1)
        return gathered

    async def wait_loop(self):  # pylint: disable=too-many-branches, too-many-statements
        """
        Waits on a loop for updates to the interface. This should not be called manually - it is handled by `send_to`.
        """

        try:  # pylint: disable=too-many-nested-blocks
            while not self.bot.is_closed():
                await asyncio.wait_for(self.send_lock_delayed(), timeout=self.timeout)

                self.update_view()

                try:
                    await self.message.edit(**self.send_kwargs)
                except discord.NotFound:
                    # something terrible has happened
                    return

        except (asyncio.CancelledError, asyncio.TimeoutError) as exception:
            self.close_exception = exception

            if self.bot.is_closed():
                # Can't do anything about the messages, so just close out to avoid noisy error
                return

            # If the message was already deleted, this part is unnecessary
            if not self.message:
                return

            if self.delete_message:
                await self.message.delete()
            else:
                await self.message.edit(view=None)

    async def interaction_check(self, interaction: discord.Interaction):
        """Check that determines whether this interaction should be honored"""
        return not self.owner or interaction.user.id == self.owner.id

    @ui.button(label="1 \u200b \N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}", style=discord.ButtonStyle.secondary)
    async def button_start(self, button: ui.Button, interaction: discord.Interaction):  # pylint: disable=unused-argument
        """Button to send interface to first page"""

        self._display_page = 0
        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="\N{BLACK LEFT-POINTING TRIANGLE}", style=discord.ButtonStyle.secondary)
    async def button_previous(self, button: ui.Button, interaction: discord.Interaction):  # pylint: disable=unused-argument
        """Button to send interface to previous page"""

        self._display_page -= 1
        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="1", style=discord.ButtonStyle.primary)
    async def button_current(self, button: ui.Button, interaction: discord.Interaction):  # pylint: disable=unused-argument
        """Button to refresh the interface"""

        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="\N{BLACK RIGHT-POINTING TRIANGLE}", style=discord.ButtonStyle.secondary)
    async def button_next(self, button: ui.Button, interaction: discord.Interaction):  # pylint: disable=unused-argument
        """Button to send interface to next page"""

        self._display_page += 1
        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR} \u200b 1", style=discord.ButtonStyle.secondary)
    async def button_last(self, button: ui.Button, interaction: discord.Interaction):  # pylint: disable=unused-argument
        """Button to send interface to last page"""

        self._display_page = self.page_count - 1
        self.update_view()
        await interaction.response.edit_message(**self.send_kwargs)

    @ui.button(label="\N{BLACK SQUARE FOR STOP} \u200b Close paginator", style=discord.ButtonStyle.danger)
    async def button_close(self, button: ui.Button, interaction: discord.Interaction):  # pylint: disable=unused-argument
        """Button to close the interface"""

        message = self.message
        self.message = None
        self.task.cancel()
        self.stop()
        await message.delete()


class PaginatorEmbedInterface(PaginatorInterface):
    """
    A subclass of :class:`PaginatorInterface` that encloses content in an Embed.
    """

    def __init__(self, *args, **kwargs):
        self._embed = kwargs.pop('embed', None) or discord.Embed()
        super().__init__(*args, **kwargs)

    @property
    def send_kwargs(self) -> dict:
        self._embed.description = self.pages[self.display_page]
        return {'embed': self._embed, 'view': self}

    max_page_size = 2048

    @property
    def page_size(self) -> int:
        return self.paginator.max_size
