# -*- coding: utf-8 -*-


REPL_COROUTINE_FORMAT = """
async def __repl_coroutine(_ctx, _msg):
    {}
"""


def humanize_relative_time(seconds: float):
    if round(seconds, 2) == 0:
        return 'now'  # negligible time distance

    if seconds < 0:
        seconds = abs(seconds)
        past = True  # append 'ago' when creating string
    else:
        past = False

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)

    seconds = round(seconds, 2)  # human-friendly numbers thanks

    units = (weeks, 'week'), (days, 'day'), (hours, 'hour'), (minutes, 'minute'), (seconds, 'second')

    formatted_unit_list = []
    for measurement, unit in units:
        if not measurement:
            continue
        formatted_unit_list.append('{} {}'.format(measurement, unit + ('s' if measurement-1 else '')))

    return ', '.join(formatted_unit_list) + (' ago' if past else '')


def cleanup_codeblock(code: str):
    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    return code.strip("`\n")


def repl_coro(code: str):
    return REPL_COROUTINE_FORMAT.format("\n    ".join(code.split("\n")))
