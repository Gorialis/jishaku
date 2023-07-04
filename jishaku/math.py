# -*- coding: utf-8 -*-

"""
jishaku.math
~~~~~~~~~~~~

Constants and functions related to math and statistical processing for jishaku

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import math
import typing


def natural_size(size_in_bytes: int) -> str:
    """
    Converts a number of bytes to an appropriately-scaled unit
    E.g.:
        1024 -> 1.00 KiB
        12345678 -> 11.77 MiB
    """
    units = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')

    power = int(math.log(max(abs(size_in_bytes), 1), 1024))

    return f"{size_in_bytes / (1024 ** power):.2f} {units[power]}"


def natural_time(time_in_seconds: float) -> str:
    """
    Converts a time in seconds to a 6-padded scaled unit
    E.g.:
        1.5000 ->   1.50  s
        0.1000 -> 100.00 ms
        0.0001 -> 100.00 us
    """
    units = (
        ('mi', 60),
        (' s', 1),
        ('ms', 1e-3),
        ('\N{GREEK SMALL LETTER MU}s', 1e-6),
    )

    absolute = abs(time_in_seconds)

    for label, size in units:
        if absolute > size:
            return f"{time_in_seconds / size:6.2f} {label}"

    return f"{time_in_seconds / 1e-9:6.2f} ns"


def mean_stddev(collection: typing.Collection[float]) -> typing.Tuple[float, float]:
    """
    Takes a collection of floats and returns (mean, stddev) as a tuple.
    """

    average = sum(collection) / len(collection)

    if len(collection) > 1:
        stddev = math.sqrt(sum(math.pow(reading - average, 2) for reading in collection) / (len(collection) - 1))
    else:
        stddev = 0.0

    return (average, stddev)


def format_stddev(collection: typing.Collection[float]) -> str:
    """
    Takes a collection of floats and produces a mean (+ stddev, if multiple values exist) string.
    """
    if len(collection) > 1:
        average, stddev = mean_stddev(collection)

        return f"{natural_time(average)} \N{PLUS-MINUS SIGN} {natural_time(stddev)}"

    return natural_time(sum(collection) / len(collection))


BARGRAPH_BLOCKS = (
    (0 / 8, "\N{LEFT ONE EIGHTH BLOCK}"),
    (1 / 8, "\N{LEFT ONE QUARTER BLOCK}"),
    (2 / 8, "\N{LEFT THREE EIGHTHS BLOCK}"),
    (3 / 8, "\N{LEFT HALF BLOCK}"),
    (4 / 8, "\N{LEFT FIVE EIGHTHS BLOCK}"),
    (5 / 8, "\N{LEFT THREE QUARTERS BLOCK}"),
    (6 / 8, "\N{LEFT SEVEN EIGHTHS BLOCK}"),
    (7 / 8, "\N{FULL BLOCK}"),
)


def get_single_bargraph_block(value: float) -> str:
    """
    Where value is a float from 0 to 1, returns a unicode block character that represents that percentage with a filled block character.
    """
    mapping = BARGRAPH_BLOCKS[0]

    for maybe_mapping in BARGRAPH_BLOCKS:
        if value > maybe_mapping[0]:
            mapping = maybe_mapping

    return mapping[1]


def format_bargraph(value: float, blocks: int) -> str:
    """
    Where value is a float from 0 to 1, returns a unicode representation of a bar of that percentage, using `blocks` unicode block characters
    """

    filled_blocks, percentage = divmod(max(min(value, 1.0), 0.0) * blocks, 1.0)

    fill = ("\N{FULL BLOCK}" * int(filled_blocks)) + (get_single_bargraph_block(percentage) if percentage > 0.0 else "")

    return fill + (" " * (blocks - len(fill)))
