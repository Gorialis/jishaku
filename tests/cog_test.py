from discord.ext import commands


def test_load_and_functionality():
    bot = commands.Bot(".")
    bot.load_extension("jishaku")
    cog = bot.get_cog("Jishaku")
    assert cog

    assert cog.sh_backend("echo hi") == "```prolog\nhi\n```"

    bot.loop.run_until_complete(bot.http.close())
