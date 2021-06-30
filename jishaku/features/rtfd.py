# -*- coding: utf-8 -*-
"""
jishaku.features.rtfd
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The jishaku rtfd-related commands.
Original credit goes to Danny (Rapptz)
https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/api.py

:copyright: (c) 2021 Danny (Rapptz), Clari, Devon (Gorialis) R
:license: Mozilla Public License 2.0 (https://mozilla.org/MPL/2.0/)
Exhibit A - Source Code Form License Notice
-------------------------------------------

  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

If it is not possible or desirable to put the notice in a particular
file, then You may include the notice in a location (such as a LICENSE
file in a relevant directory) where a recipient would be likely to look
for such a notice.

You may add additional accurate notices of copyright ownership.
"""

import io
import re
import os
import zlib
import discord
from discord.ext import commands

from jishaku.features.baseclass import Feature


def fuzzyfinder(text, collection, *, key=None, lazy=True):
    """
    Fuzzy search from R. Danny's utils
    """
    suggestions = []
    text = str(text)
    pat = '.*?'.join(map(re.escape, text))
    regex = re.compile(pat, flags=re.IGNORECASE)
    for item in collection:
        to_search = key(item) if key else item
        r = regex.search(to_search)  # pylint: disable=invalid-name
        if r:
            suggestions.append((len(r.group()), r.start(), item))

    def sort_key(tup):
        if key:
            return tup[0], tup[1], key(tup[2])
        return tup

    if lazy:
        return (z for _, _, z in sorted(suggestions, key=sort_key))
    else:
        return [z for _, _, z in sorted(suggestions, key=sort_key)]


class SphinxObjectFileReader:
    """
    Inspired by Sphinx's InventoryFileReader
    "Borrowed" from R. Danny for RTFD.
    """
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = io.BytesIO(buffer)

    def readline(self):  # pylint: disable=missing-function-docstring
        return self.stream.readline().decode('utf-8')

    def skipline(self):  # pylint: disable=missing-function-docstring
        self.stream.readline()

    def read_compressed_chunks(self):  # pylint: disable=missing-function-docstring
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):  # pylint: disable=missing-function-docstring
        buf = b''
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b'\n')
            while pos != -1:
                yield buf[:pos].decode('utf-8')
                buf = buf[pos + 1:]
                pos = buf.find(b'\n')


class RTFD(Feature):
    """
    Feature containing documentation commands for ease of access, courtesy of R. Danny.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rtfm_cache = {}

    def parse_object_inv(self, stream, url):  # pylint: disable=missing-function-docstring
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != '# Sphinx inventory version 2':
            raise RuntimeError('Invalid objects.inv file version.')

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]  # noqa: F841, pylint: disable=unused-variable

        # next line says if it's a zlib header
        line = stream.readline()
        if 'zlib' not in line:
            raise RuntimeError('Invalid objects.inv file, not z-lib compatible.')

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r'(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)')
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()  # pylint: disable=unused-variable
            domain, _, subdirective = directive.partition(':')
            if directive == 'py:module' and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == 'std:doc':
                subdirective = 'label'

            if location.endswith('$'):
                location = location[:-1] + name

            key = name if dispname == '-' else dispname
            prefix = f'{subdirective}:' if domain == 'std' else ''

            if projname == 'discord.py':
                key = key.replace('discord.ext.commands.', '').replace('discord.', '')

            result[f'{prefix}{key}'] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self, page_types):  # pylint: disable=missing-function-docstring
        cache = {}
        for key, page in page_types.items():
            cache[key] = {}
            async with self.session.get(page + '/objects.inv') as resp:
                if resp.status != 200:
                    raise RuntimeError('Cannot build rtfm lookup table, try again later.')

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)
        self._rtfm_cache = cache

    async def do_rtfm(self, ctx: commands.Context, key, obj):
        """
        The actual implementation of the RTFD command.
        """
        page_types = {
            'latest': 'https://discordpy.readthedocs.io/en/latest',
            'latest-jp': 'https://discordpy.readthedocs.io/ja/latest',
            'python': 'https://docs.python.org/3',
            'python-jp': 'https://docs.python.org/ja/3',
            'master': 'https://discordpy.readthedocs.io/en/master',
        }

        if obj is None:
            await ctx.send(page_types[key])
            return

        if not getattr(self, '_rtfm_cache', {}):
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(page_types)

        obj = re.sub(r'^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)', r'\1', obj)

        if key.startswith('latest'):
            # point the abc.Messageable types properly:
            q = obj.lower()  # pylint: disable=invalid-name
            for name in dir(discord.abc.Messageable):
                if name[0] == '_':
                    continue
                if q == name:
                    obj = f'abc.Messageable.{name}'
                    break

        cache = list(self._rtfm_cache.get(key, {}).items())

        matches = fuzzyfinder(obj, cache, key=lambda t: t[0], lazy=False)[:8]

        e = discord.Embed(colour=discord.Colour.blurple())  # pylint: disable=invalid-name
        if len(matches) == 0:
            return await ctx.send('Could not find anything. Sorry.')

        e.description = '\n'.join(f'[`{key}`]({url})' for key, url in matches)
        await ctx.send(embed=e, reference=ctx.message.reference)

    @Feature.Command(parent="jsk", name="rtfd", aliases=['rtfm'], invoke_without_command=True)
    async def jsk_rtfd(self, ctx: commands.Context, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity.
        Events, objects, and functions are all supported through a
        a cruddy fuzzy algorithm.
        """
        await self.do_rtfm(ctx, "latest", obj)

    @Feature.Command(parent="jsk_rtfd", name="jp")
    async def rtfm_jp(self, ctx: commands.Context, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (Japanese)."""
        await self.do_rtfm(ctx, 'latest-jp', obj)

    @Feature.Command(parent="jsk_rtfd", name='python', aliases=['py'])
    async def rtfm_python(self, ctx: commands.Context, *, obj: str = None):
        """Gives you a documentation link for a Python entity."""
        await self.do_rtfm(ctx, "latest", obj)

    @Feature.Command(parent="jsk_rtfd", name='py-jp', aliases=['py-ja'])
    async def rtfm_python_jp(self, ctx: commands.Context, *, obj: str = None):
        """Gives you a documentation link for a Python entity (Japanese)."""
        await self.do_rtfm(ctx, 'python-jp', obj)

    @Feature.Command(parent="jsk_rtfd", name='master', aliases=['2.0'])
    async def rtfm_master(self, ctx: commands.Context, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (master branch)"""
        await self.do_rtfm(ctx, 'master', obj)
