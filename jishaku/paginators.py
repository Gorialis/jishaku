# -*- coding: utf-8 -*-

"""
jishaku.paginators
~~~~~~~~~~~~~~~~~~

Paginator-related tools and interfaces for Jishaku.

:copyright: (c) 2019 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import asyncio
import collections
import re

import discord
from discord.ext import commands

from jishaku.hljs import get_language

__all__ = ('EmojiSettings', 'PaginatorInterface', 'PaginatorEmbedInterface',
           'WrappedPaginator', 'FilePaginator')


# emoji settings, this sets what emoji are used for PaginatorInterface
EmojiSettings = collections.namedtuple('EmojiSettings', 'start back forward end close')

EMOJI_DEFAULT = EmojiSettings(
    start="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
    back="\N{BLACK LEFT-POINTING TRIANGLE}",
    forward="\N{BLACK RIGHT-POINTING TRIANGLE}",
    end="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
    close="\N{BLACK SQUARE FOR STOP}"
)


class PaginatorInterface:  # pylint: disable=too-many-instance-attributes
    """
    A message and reaction based interface for paginators.
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
        self.update_lock: asyncio.Lock = asyncio.Semaphore(value=kwargs.pop('update_max', 2))

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

        display_page = self.display_page
        page_num = f'\nPage {display_page + 1}/{self.page_count}'
        content = self.pages[display_page] + page_num
        return {'content': content}

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
            self.bot.loop.create_task(self.update())

    async def send_to(self, destination: discord.abc.Messageable):
        """
        Sends a message to the given destination with this interface.

        This automatically creates the response task for you.
        """

        self.message = await destination.send(**self.send_kwargs)

        # add the close reaction
        await self.message.add_reaction(self.emojis.close)

        # if there is more than one page, and the reactions haven't been sent yet, send navigation emotes
        if not self.sent_page_reactions and self.page_count > 1:
            await self.send_all_reactions()

        if self.task:
            self.task.cancel()

        self.task = self.bot.loop.create_task(self.wait_loop())

    async def send_all_reactions(self):
        """
        Sends all reactions for this paginator, if any are missing.

        This method is generally for internal use only.
        """

        for emoji in filter(None, self.emojis):
            await self.message.add_reaction(emoji)
        self.sent_page_reactions = True

    @property
    def closed(self):
        """
        Is this interface closed?
        """

        if not self.task:
            return False
        return self.task.done()

    async def wait_loop(self):
        """
        Waits on a loop for reactions to the message. This should not be called manually - it is handled by `send_to`.
        """

        start, back, forward, end, close = self.emojis

        def check(payload: discord.RawReactionActionEvent):
            """
            Checks if this reaction is related to the paginator interface.
            """

            owner_check = not self.owner or payload.user_id == self.owner.id

            emoji = payload.emoji
            if isinstance(emoji, discord.PartialEmoji) and emoji.is_unicode_emoji():
                emoji = emoji.name

            return payload.message_id == self.message.id and \
                emoji and emoji in self.emojis and \
                payload.user_id != self.bot.user.id and owner_check

        try:
            while not self.bot.is_closed():
                payload = await self.bot.wait_for('raw_reaction_add', check=check, timeout=self.timeout)

                emoji = payload.emoji
                if isinstance(emoji, discord.PartialEmoji) and emoji.is_unicode_emoji():
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

                self.bot.loop.create_task(self.update())

                try:
                    await self.message.remove_reaction(payload.emoji, discord.Object(id=payload.user_id))
                except discord.Forbidden:
                    pass

        except asyncio.TimeoutError:
            if self.delete_message:
                return await self.message.delete()

            for emoji in filter(None, self.emojis):
                try:
                    await self.message.remove_reaction(emoji, self.message.guild.me)
                except (discord.Forbidden, discord.NotFound):
                    pass

    async def update(self):
        """
        Updates this interface's messages with the latest data.
        """

        if self.update_lock.locked():
            return

        async with self.update_lock:
            if self.update_lock.locked():
                # if this engagement has caused the semaphore to exhaust,
                # we are overloaded and need to calm down.
                await asyncio.sleep(1)

            if not self.message:
                # too fast, stagger so this update gets through
                await asyncio.sleep(0.5)

            if not self.sent_page_reactions and self.page_count > 1:
                self.bot.loop.create_task(self.send_all_reactions())
                self.sent_page_reactions = True  # don't spawn any more tasks

            await self.message.edit(**self.send_kwargs)


class PaginatorEmbedInterface(PaginatorInterface):
    """
    A subclass of :class:`PaginatorInterface` that encloses content in an Embed.
    """

    def __init__(self, *args, **kwargs):
        self._embed = kwargs.pop('embed', None) or discord.Embed()
        super().__init__(*args, **kwargs)

    @property
    def send_kwargs(self) -> dict:
        display_page = self.display_page
        self._embed.description = self.pages[display_page]
        self._embed.set_footer(text=f'Page {display_page + 1}/{self.page_count}')
        return {'embed': self._embed}

    max_page_size = 2048

    @property
    def page_size(self) -> int:
        return self.paginator.max_size


class WrappedPaginator(commands.Paginator):
    """
    A paginator that allows automatic wrapping of lines should they not fit.

    This is useful when paginating unpredictable output,
    as it allows for line splitting on big chunks of data.

    Delimiters are prioritized in the order of their tuple.

    Arguments
    ---------
    wrap_on: tuple
        A tuple of wrapping delimiters.
    include_wrapped: bool
        Whether to include the delimiter at the start of the new wrapped line.
    """

    def __init__(self, *args, wrap_on=('\n', ' '), include_wrapped=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.wrap_on = wrap_on
        self.include_wrapped = include_wrapped

    def add_line(self, line='', *, empty=False):
        true_max_size = self.max_size - len(self.prefix) - 2

        while len(line) > true_max_size:
            search_string = line[0:true_max_size - 1]
            wrapped = False

            for delimiter in self.wrap_on:
                position = search_string.rfind(delimiter)

                if position > 0:
                    super().add_line(line[0:position], empty=empty)
                    wrapped = True

                    if self.include_wrapped:
                        line = line[position:]
                    else:
                        line = line[position + len(delimiter):]

                    break

            if not wrapped:
                break  # this will probably always cause an exception

        super().add_line(line, empty=empty)


class FilePaginator(commands.Paginator):
    """
    A paginator of syntax-highlighted codeblocks, read from a file-like.

    Arguments
    ----------
    fp
        A file-like (implements ``fp.read``) to read the data for this paginator from.
    line_span: Optional[Tuple[int, int]]
        A linespan to read from the file. If None, reads the whole file.
    """

    __encoding_regex = re.compile(br'coding[=:]\s*([-\w.]+)')

    def __init__(self, fp, line_span=None, **kwargs):
        language = ''

        try:
            language = get_language(fp.name)
        except AttributeError:
            pass

        raw_content = fp.read()

        try:
            lines = raw_content.decode('utf-8').split('\n')
        except UnicodeDecodeError as exc:
            # This file isn't UTF-8.

            #  By Python and text-editor convention,
            # there may be a hint as to what the actual encoding is
            # near the start of the file.

            encoding_match = self.__encoding_regex.search(raw_content[:128])

            if encoding_match:
                encoding = encoding_match.group(1)
            else:
                raise exc

            try:
                lines = raw_content.decode(encoding.decode('utf-8')).split('\n')
            except UnicodeDecodeError as exc2:
                raise exc2 from exc

        del raw_content

        first_line = lines[0]

        # If the first line is a shebang,
        if first_line.startswith('#!'):
            # prioritize its declaration over the extension.
            language = get_language(first_line) or language

        super().__init__(prefix=f'```{language}', suffix='```', **kwargs)

        line_number = len(lines)

        if line_span:
            line_span = sorted(line_span)
            if min(line_span) < 1 or max(line_span) > line_number:
                raise ValueError("Linespan goes out of bounds.")
            lines = lines[line_span[0] - 1:line_span[1]]

        for line in lines:
            self.add_line(line)


class WrappedFilePaginator(FilePaginator, WrappedPaginator):
    """
    Combination of FilePaginator and WrappedPaginator.
    In other words, a FilePaginator that supports line wrapping.
    """
