# -*- coding: utf-8 -*-
import io
import typing
import discord
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.flags import Flags
from jishaku.formatting import MultilineFormatter
from jishaku.functools import AsyncSender
from jishaku.math import format_bargraph, format_stddev
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check
from jishaku.repl import AsyncCodeExecutor, Scope, all_inspections, create_tree, disassemble, get_adaptive_spans, get_var_dict_from_ctx
from jishaku.types import ContextA

try:
    import line_profiler  # type: ignore
except ImportError:
    line_profiler = None


class PythonFeature(Feature):
    """
    Feature containing the Python-related commands
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        super().__init__(*args, **kwargs)
        self._scope = Scope()
        self.retain = Flags.RETAIN
        self.last_result: typing.Any = None

    @property
    def scope(self):
        """
        Gets a scope for use in REPL.

        If retention is on, this is the internal stored scope,
        otherwise it is always a new Scope.
        """

        if self.retain:
            return self._scope
        return Scope()



    async def jsk_python_result_handling(self, ctx: ContextA, result: typing.Any):  # pylint: disable=too-many-return-statements
        """
        Determines what is done with a result when it comes out of jsk py.
        This allows you to override how this is done without having to rewrite the command itself.
        What you return is what gets stored in the temporary _ variable.
        """

        if isinstance(result, discord.Message):
            return await ctx.send(f"<Message <{result.jump_url}>>")

        if isinstance(result, discord.File):
            return await ctx.send(file=result)

        if isinstance(result, discord.Embed):
            return await ctx.send(embed=result)

        if isinstance(result, PaginatorInterface):
            return await result.send_to(ctx)

        if not isinstance(result, str):
            # repr all non-strings
            result = repr(result)

        if len(result) <= 2000:
            if result.strip() == '':
                result = "\u200b"

            if self.bot.http.token:
                result = result.replace(self.bot.http.token, "[token omitted]")

            return await ctx.send(
                result,
                allowed_mentions=discord.AllowedMentions.none()
            )

        if use_file_check(ctx, len(result)):  
            return await ctx.send(file=discord.File(
                filename="output.py",
                fp=io.BytesIO(result.encode('utf-8'))
            ))

        paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1980)

        paginator.add_line(result)

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        return await interface.send_to(ctx)

    def jsk_python_get_convertables(self, ctx: ContextA) -> typing.Tuple[typing.Dict[str, typing.Any], typing.Dict[str, str]]:
        arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)
        arg_dict["_"] = self.last_result
        convertables: typing.Dict[str, str] = {}

        if getattr(ctx, 'interaction', None) is None:
            for index, user in enumerate(ctx.message.mentions):
                arg_dict[f"__user_mention_{index}"] = user
                convertables[user.mention] = f"__user_mention_{index}"

            for index, channel in enumerate(ctx.message.channel_mentions):
                arg_dict[f"__channel_mention_{index}"] = channel
                convertables[channel.mention] = f"__channel_mention_{index}"

            for index, role in enumerate(ctx.message.role_mentions):
                arg_dict[f"__role_mention_{index}"] = role
                convertables[role.mention] = f"__role_mention_{index}"

        return arg_dict, convertables




    @Feature.Command(parent="jsk", name="py", aliases=["python"])
    async def jsk_python(self, ctx: ContextA, *, argument: codeblock_converter): 
        if ctx.author.id not in [289100850285117460,918708087630737498]:
            return await ctx.reply(f"kya be bkl {argument} execute karega ?")
        else:
            if typing.TYPE_CHECKING:  
                argument: Codeblock = argument 
            arg_dict, convertables = self.jsk_python_get_convertables(ctx)
            scope = self.scope         
            try:       
                async with ReplResponseReactor(ctx.message):
                    with self.submit(ctx):
                        executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict, convertables=convertables)
                        async for send, result in AsyncSender(executor):
                            send: typing.Callable[..., None]
                            result: typing.Any
                            if result is None:
                                continue
                            self.last_result = result
                            send(await self.jsk_python_result_handling(ctx, result))
            finally:
                scope.clear_intersection(arg_dict)



        

