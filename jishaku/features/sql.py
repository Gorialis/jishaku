# -*- coding: utf-8 -*-

"""
jishaku.features.sql
~~~~~~~~~~~~~~~~~~~~

The jishaku SQL-related commands and utilities.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import contextlib
import collections
import io
import typing

import discord
from tabulate import tabulate

from jishaku.types import ContextA

from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.paginators import use_file_check, PaginatorInterface, WrappedPaginator


T = typing.TypeVar('T')


class Adapter(typing.Generic[T]):
    """
    Base class to genericize operations between different SQL adapters
    """

    def __init__(self, connector: T):
        self.connector = connector

    @contextlib.asynccontextmanager
    async def use(self):
        """
        Async context manager that must be active for other elements of this Adapter to be guaranteed usable.

        This can do things like acquire from a pool or open a new connection.
        """
        yield

    def info(self) -> str:
        """
        A string summarizing this adapter's exposable information about its connection.

        This should include things like the adapter kind, and any ascertainable info about the server it connects to.
        """
        raise NotImplementedError()

    async def fetchrow(self, query: str) -> typing.Dict[str, typing.Any]:
        """
        A function that executes a fetch-style request and returns a single entry of {column: value}.
        """
        raise NotImplementedError()

    async def fetch(self, query: str) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        A function that executes a fetch-style request and returns possibly many entries of {column: value}.
        """
        raise NotImplementedError()

    async def execute(self, query: str) -> str:
        """
        A function that executes a execute-style request and returns a status string.
        """
        raise NotImplementedError()

    async def table_summary(self, table_query: typing.Optional[str]) -> typing.Dict[str, typing.Dict[str, str]]:
        """
        A function that queries to find table structures identified by this adapter.

        Returns a dictionary in form
        {
            table: {
                column: remarks
            }
        }
        """
        raise NotImplementedError()


KNOWN_ADAPTERS: typing.Dict[typing.Type[typing.Any], typing.Type[Adapter[typing.Any]]] = {}


def adapter(*types: typing.Type[typing.Any]):
    """
    Wraps an adapter class, adding it to the list of globally known adapters and then returning it.
    """

    def wrapper(klass: typing.Type[Adapter[typing.Any]]):
        for handled_type in types:
            KNOWN_ADAPTERS[handled_type] = klass
        return klass

    return wrapper

# pylint: disable=missing-class-docstring,missing-function-docstring


try:
    import asyncpg  # type: ignore
except ImportError:
    pass
else:
    @adapter(asyncpg.Connection, asyncpg.Pool)
    class AsyncpgConnectionAdapter(Adapter[asyncpg.Connection | asyncpg.Pool]):
        def __init__(self, connection: asyncpg.Connection | asyncpg.Pool):
            super().__init__(connection)
            self.connection: asyncpg.Connection = None  # type: ignore

        @contextlib.asynccontextmanager
        async def use(self):
            if isinstance(self.connector, asyncpg.Pool):
                async with self.connector.acquire() as connection:  # type: ignore
                    self.connection = connection  # type: ignore
                    yield
            else:
                self.connection = self.connector
                yield

        def info(self) -> str:
            return " ".join((
                f"asyncpg {asyncpg.__version__} {type(self.connector).__name__} connected to",
                f"PostgreSQL server {'.'.join(str(x) for x in self.connection.get_server_version())}",  # type: ignore
                f"on PID {self.connection.get_server_pid()}",
            ))

        async def fetchrow(self, query: str) -> typing.Dict[str, typing.Any]:
            return dict(await self.connection.fetchrow(query))  # type: ignore

        async def fetch(self, query: str) -> typing.List[typing.Dict[str, typing.Any]]:
            return [
                dict(record)  # type: ignore
                for record in await self.connection.fetch(query)  # type: ignore
            ]

        async def execute(self, query: str) -> str:
            return await self.connection.execute(query)  # type: ignore

        async def table_summary(self, table_query: typing.Optional[str]) -> typing.Dict[str, typing.Dict[str, str]]:
            tables: typing.Dict[str, typing.Dict[str, str]] = collections.defaultdict(dict)

            for record in await self.connection.fetch(  # type: ignore
                """
                SELECT * FROM information_schema.columns
                WHERE $1::TEXT IS NULL OR table_name = $1::TEXT
                ORDER BY
                table_schema = 'pg_catalog' ASC,
                table_schema = 'information_schema' ASC,
                table_catalog ASC,
                table_schema ASC,
                table_name ASC,
                ordinal_position ASC
                """,
                table_query
            ):
                table_name: str = f"{record['table_catalog']}.{record['table_schema']}.{record['table_name']}"  # type: ignore
                tables[table_name][record['column_name']] = (  # type: ignore
                    record['data_type'].upper() + (' NOT NULL' if record['is_nullable'] == 'NO' else '')  # type: ignore
                )

            return tables


# pylint: enable=missing-class-docstring,missing-function-docstring

class SQLFeature(Feature):
    """
    Feature containing SQL-related commands
    """

    JSK_TRY_ATTRIBUTES = ('database_pool', 'database', 'db_pool', 'db', 'pool')

    def jsk_find_adapter(self, ctx: ContextA) -> typing.Union[typing.Tuple[Adapter[typing.Any], str], typing.Tuple[None, None]]:
        """
        Attempts to search for a working database adapter, returning (Adapter, location) if one is found.
        """

        for name_a, source in (('ctx', ctx), ('bot', ctx.bot)):
            for attribute in self.JSK_TRY_ATTRIBUTES:
                maybe_adapter = getattr(source, attribute, None)

                if maybe_adapter is None:
                    continue

                for adapter_class, adapter_shim in KNOWN_ADAPTERS.items():
                    if isinstance(maybe_adapter, adapter_class):
                        return adapter_shim(maybe_adapter), f"{name_a}.{attribute}"

        return None, None

    @Feature.Command(parent="jsk", name="sql", invoke_without_command=True, ignore_extra=False)
    async def jsk_sql(self, ctx: ContextA):
        """
        Parent for SQL adapter related commands
        """

        adapter_shim, location = self.jsk_find_adapter(ctx)

        if adapter_shim is None:
            return await ctx.send("No SQL adapter could be found on this bot.")

        async with adapter_shim.use():
            return await ctx.send(f"Using {adapter_shim.info()} found at `{location}`")

    @Feature.Command(parent="jsk_sql", name="fetchrow", aliases=["fetchone"])
    async def jsk_sql_fetchrow(self, ctx: ContextA, *, query: str):
        """
        Fetch a single row from the SQL database.
        """

        adapter_shim, _ = self.jsk_find_adapter(ctx)

        if adapter_shim is None:
            return await ctx.send("No SQL adapter could be found on this bot.")

        async with adapter_shim.use():
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    output = await adapter_shim.fetchrow(query)

        text = tabulate({key: [value] for key, value in output}, headers='keys', tablefmt='psql')

        if use_file_check(ctx, len(text)):
            await ctx.reply(file=discord.File(
                filename="response.txt",
                fp=io.BytesIO(text.encode('utf-8'))
            ))
        else:
            paginator = WrappedPaginator(max_size=1980)
            paginator.add_line(text)

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            await interface.send_to(ctx)

    @Feature.Command(parent="jsk_sql", name="fetch")
    async def jsk_sql_fetch(self, ctx: ContextA, *, query: str):
        """
        Fetch multiple rows from the SQL database.
        """

        adapter_shim, _ = self.jsk_find_adapter(ctx)

        if adapter_shim is None:
            return await ctx.send("No SQL adapter could be found on this bot.")

        async with adapter_shim.use():
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    output = await adapter_shim.fetch(query)

        aggregator: typing.Dict[str, typing.List[typing.Any]] = collections.defaultdict(list)

        for record in output:
            for key, value in record.items():
                aggregator[key].append(value)

        text = tabulate(aggregator, headers='keys', tablefmt='psql')

        if use_file_check(ctx, len(text)):
            await ctx.reply(file=discord.File(
                filename="response.txt",
                fp=io.BytesIO(text.encode('utf-8'))
            ))
        else:
            paginator = WrappedPaginator(max_size=1980)
            paginator.add_line(text)

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            await interface.send_to(ctx)

    @Feature.Command(parent="jsk_sql", name="select", aliases=['SELECT'])
    async def jsk_sql_select(self, ctx: ContextA, *, query: str):
        """
        Shortcut for 'jsk sql fetch select'.
        """

        await ctx.invoke(self.jsk_sql_fetch, query=f'SELECT {query}')  # type: ignore

    @Feature.Command(parent="jsk_sql", name="execute")
    async def jsk_sql_execute(self, ctx: ContextA, *, query: str):
        """
        Executes a statement against the SQL database.
        """

        adapter_shim, _ = self.jsk_find_adapter(ctx)

        if adapter_shim is None:
            return await ctx.send("No SQL adapter could be found on this bot.")

        async with adapter_shim.use():
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    output = await adapter_shim.execute(query)

        await ctx.reply(content=output)

    @Feature.Command(parent="jsk_sql", name="schema")
    async def jsk_sql_schema(self, ctx: ContextA, *, query: typing.Optional[str] = None):
        """
        Executes a statement against the SQL database.
        """

        adapter_shim, _ = self.jsk_find_adapter(ctx)

        if adapter_shim is None:
            return await ctx.send("No SQL adapter could be found on this bot.")

        async with adapter_shim.use():
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    output = await adapter_shim.table_summary(query)

        paginator = WrappedPaginator(prefix='```sql', max_size=1980)

        for table, structure in output.items():
            paginator.add_line(f'{table} (')

            for column_name, remarks in structure.items():
                paginator.add_line(f'    {column_name:30} {remarks},')

            paginator.add_line(')')
            paginator.close_page()

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        await interface.send_to(ctx)
