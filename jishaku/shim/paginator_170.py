# -*- coding: utf-8 -*-

"""
jishaku.paginators (shim for discord.py 1.7.x)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Paginator-related tools and interfaces for Jishaku.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import typing

import discord
from discord.ext import commands

from jishaku.shim.paginator_base import EMOJI_DEFAULT


class PaginatorInterface:  # pylint: disable=too-many-instance-attributes
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

    def __init__(
        self,
        bot: typing.Union[commands.Bot, commands.AutoShardedBot],
        paginator: commands.Paginator,
        **kwargs: typing.Any
    ):
        if not isinstance(paginator, commands.Paginator):  # type: ignore
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

        self.task: typing.Optional[asyncio.Task[None]] = None
        self.send_lock: asyncio.Event = asyncio.Event()

        self.close_exception: typing.Optional[BaseException] = None

        if self.page_size > self.max_page_size:
            raise ValueError(
                f'Paginator passed has too large of a page size for this interface. '
                f'({self.page_size} > {self.max_page_size})'
            )

    @property
    def pages(self):
        """
        Returns the paginator's pages without prematurely closing the active page.
        """
        # protected access has to be permitted here to not close the paginator's pages

        # pylint: disable=protected-access
        paginator_pages = list(self.paginator._pages)  # type: ignore
        if len(self.paginator._current_page) > 1:  # type: ignore
            paginator_pages.append('\n'.join(self.paginator._current_page) + '\n' + (self.paginator.suffix or ''))  # type: ignore
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
    def display_page(self, value: int):
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
    def send_kwargs(self) -> typing.Dict[str, typing.Any]:
        """
        A property that returns the kwargs forwarded to send/edit when updating the page.

        As this must be compatible with both `discord.TextChannel.send` and `discord.Message.edit`,
        it should be a dict containing 'content', 'embed' or both.
        """

        display_page = self.display_page
        page_num = f'\nPage {display_page + 1}/{self.page_count}'
        content = self.pages[display_page] + page_num
        return {'content': content}

    async def add_line(self, *args: typing.Any, **kwargs: typing.Any):
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

        self.message = await destination.send(
            **self.send_kwargs, allowed_mentions=discord.AllowedMentions.none()
        )

        # add the close reaction
        await self.message.add_reaction(self.emojis.close)

        self.send_lock.set()

        if self.task:
            self.task.cancel()

        self.task = self.bot.loop.create_task(self.wait_loop())

        # if there is more than one page, and the reactions haven't been sent yet, send navigation emotes
        if not self.sent_page_reactions and self.page_count > 1:
            await self.send_all_reactions()

        return self

    async def send_all_reactions(self):
        """
        Sends all reactions for this paginator, if any are missing.

        This method is generally for internal use only.
        """

        if not self.message:
            raise RuntimeError("Message is not set on PaginatorInterface")

        for emoji in filter(None, self.emojis):
            try:
                await self.message.add_reaction(emoji)
            except discord.NotFound:
                # the paginator has probably already been closed
                break
        self.sent_page_reactions = True

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

    async def wait_loop(self):
        """
        Waits on a loop for reactions to the message. This should not be called manually - it is handled by `send_to`.
        """

        if not self.message:
            raise RuntimeError("Message not set on PaginatorInterface")

        if not self.bot.user:
            raise RuntimeError("A PaginatorInterface cannot be started while the bot is offline")

        start, back, forward, end, close = self.emojis

        def check(payload: discord.RawReactionActionEvent):
            """
            Checks if this reaction is related to the paginator interface.
            """

            owner_check = not self.owner or payload.user_id == self.owner.id

            emoji = payload.emoji
            if isinstance(emoji, discord.PartialEmoji) and emoji.is_unicode_emoji():  # type: ignore
                emoji = emoji.name

            tests = (
                owner_check,
                payload.message_id == self.message.id if self.message else False,
                emoji,
                emoji in self.emojis,
                payload.user_id != self.bot.user.id if self.bot.user else True
            )

            return all(tests)

        task_list = [
            self.bot.loop.create_task(coro) for coro in [
                self.bot.wait_for('raw_reaction_add', check=check),
                self.bot.wait_for('raw_reaction_remove', check=check),
                self.send_lock_delayed()
            ]
        ]

        try:  # pylint: disable=too-many-nested-blocks
            last_kwargs = None

            while not self.bot.is_closed():
                done, _ = await asyncio.wait(task_list, timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED)

                if not done:
                    raise asyncio.TimeoutError

                for task in done:
                    task_list.remove(task)
                    payload = task.result()

                    if isinstance(payload, discord.RawReactionActionEvent):
                        emoji = payload.emoji
                        if isinstance(emoji, discord.PartialEmoji) and emoji.is_unicode_emoji():  # type: ignore
                            emoji = emoji.name

                        if emoji == close:
                            await self.message.delete()
                            return

                        if emoji == start:
                            self._display_page = 0
                        elif emoji == end:
                            self._display_page = self.page_count - 1
                        elif emoji == back:
                            self._display_page -= 1
                        elif emoji == forward:
                            self._display_page += 1

                        if payload.event_type == 'REACTION_ADD':
                            task_list.append(self.bot.loop.create_task(
                                self.bot.wait_for('raw_reaction_add', check=check)
                            ))
                        elif payload.event_type == 'REACTION_REMOVE':
                            task_list.append(self.bot.loop.create_task(
                                self.bot.wait_for('raw_reaction_remove', check=check)
                            ))
                    else:
                        # Send lock was released
                        task_list.append(self.bot.loop.create_task(self.send_lock_delayed()))

                if not self.sent_page_reactions and self.page_count > 1:
                    self.bot.loop.create_task(self.send_all_reactions())
                    self.sent_page_reactions = True  # don't spawn any more tasks

                if self.send_kwargs != last_kwargs:
                    try:
                        await self.message.edit(**self.send_kwargs)
                    except discord.NotFound:
                        # something terrible has happened
                        return

                    last_kwargs = self.send_kwargs

        except (asyncio.CancelledError, asyncio.TimeoutError) as exception:
            self.close_exception = exception

            if self.bot.is_closed():
                # Can't do anything about the messages, so just close out to avoid noisy error
                return

            if self.delete_message:
                return await self.message.delete()

            for emoji in filter(None, self.emojis):
                try:
                    await self.message.remove_reaction(emoji, self.bot.user)
                except (discord.Forbidden, discord.NotFound):
                    pass

        finally:
            for task in task_list:
                task.cancel()


class PaginatorEmbedInterface(PaginatorInterface):
    """
    A subclass of :class:`PaginatorInterface` that encloses content in an Embed.
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        self._embed = kwargs.pop('embed', None) or discord.Embed()
        super().__init__(*args, **kwargs)

    @property
    def send_kwargs(self) -> typing.Dict[str, typing.Any]:
        display_page = self.display_page
        self._embed.description = self.pages[display_page]
        self._embed.set_footer(text=f'Page {display_page + 1}/{self.page_count}')
        return {'embed': self._embed}

    max_page_size = 2048

    @property
    def page_size(self) -> int:
        return self.paginator.max_size
