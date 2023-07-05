# -*- coding: utf-8 -*-

"""
jishaku.formatting
~~~~~~~~~~~~~~~~~~~

Advanced formatting constructs

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import dataclasses
import typing

# List of block characters:
#  - Dashed character from the left
#  - Left hand of span arm
#  - Middle bridge of span arm
#  - Right hand of span arm
#  - Extended part of arm on earlier lines to the right
#  - Extended part of arm on earlier lines to the left
BLOCK_CHARACTERS_SIMPLE = (
    '-', '|', '_', '|', '|', '|'
)

BLOCK_CHARACTERS_FANCY = (
    '-',
    '\N{BOX DRAWINGS LIGHT UP AND RIGHT}',
    '\N{BOX DRAWINGS LIGHT HORIZONTAL}',
    '\N{BOX DRAWINGS LIGHT UP AND LEFT}',
    '\N{BOX DRAWINGS LIGHT VERTICAL}',
    '\N{BOX DRAWINGS LIGHT VERTICAL}'
)


@dataclasses.dataclass
class LineAnnotation:
    """
    A line annotation contains:
    - Annotation text
    - A span (start and end point)
    - An (optional) ANSI code for the annotation text and line
    - An (optional) ANSI code for the annotated text's foreground
    - An (optional) ANSI code for the annotated text's background
    """

    text: str
    span: typing.Optional[typing.Tuple[int, int]]
    annotation_ansi: typing.Union[typing.Sequence[int], int, None] = None
    text_foreground: typing.Optional[int] = None
    text_background: typing.Optional[int] = None


class LineFormatter:
    """
    Class that formats a single line with a list of ordered annotations like so:

            one (two three) four
    FOO ‐‐‐‐└─┘ ││ │ │   ││ │  │
    BAR ‐‐‐‐‐‐‐‐└─────────┘ │  │
    BAZ ‐‐‐‐‐‐‐‐‐└─┘ │   │  │  │
    FOO ‐‐‐‐‐‐‐‐‐‐‐‐‐└───┘  │  │
    BAR ‐‐‐‐‐‐‐‐‐‐‐‐‐‐‐‐‐‐‐‐└──┘

    """
    def __init__(self, line: str):
        self.line: str = line
        self.max_annotation_size: int = 0
        self.annotations: typing.List[LineAnnotation] = []

    def add_annotation(
        self,
        text: str, span: typing.Optional[typing.Tuple[int, int]],
        annotation_ansi: typing.Union[typing.Sequence[int], int, None] = None,
        text_foreground: typing.Optional[int] = None,
        text_background: typing.Optional[int] = None
    ):
        """
        Add an annotation to the line formatter.
        The order in which the annotations are added matters.
        """

        # Flip the span order if right is earlier than left
        if span and span[0] > span[1]:
            span = (span[1], span[0])

        self.max_annotation_size = max(self.max_annotation_size, len(text))
        self.annotations.append(LineAnnotation(text, span, annotation_ansi, text_foreground, text_background))

    def output(self, use_complex: bool = True, use_ansi: bool = False) -> str:
        """
        Output the line and associated annotations, optionally with color
        """

        lines: typing.List[str] = []
        block = BLOCK_CHARACTERS_FANCY if use_complex else BLOCK_CHARACTERS_SIMPLE

        # The main line
        if use_ansi:
            spans = [
                (annotation.span, annotation.text_foreground, annotation.text_background)
                for annotation in self.annotations
                if annotation.span and (annotation.text_foreground or annotation.text_background)
            ]

            if spans:
                # Sort spans by shortest and earliest first
                spans.sort(key=lambda s: (s[0][1] - s[0][0], s[0][0]))

                line = [" " * (self.max_annotation_size + 2)]
                color = (None, None)

                for index, character in enumerate(self.line):
                    foreground = None
                    background = None

                    for span in spans:
                        if span[0][0] <= index <= span[0][1]:
                            if foreground is None and span[1] is not None:
                                foreground = span[1]
                            if background is None and span[2] is not None:
                                background = span[2]

                        if foreground is not None and background is not None:
                            break

                    if (foreground, background) != color:
                        line.append(
                            "\u001b[0"
                            + (f';{foreground}' if foreground else '')
                            + (f';{background}' if background else '')
                            + 'm'
                            + character
                        )
                    else:
                        line.append(character)

                    color = (foreground, background)

                if color != (None, None):
                    line.append("\u001b[0m")

                lines.append("".join(line))

            else:
                # No spans, so optimize by just skipping bothering
                lines.append(" " * (self.max_annotation_size + 2) + self.line)
        else:
            lines.append(" " * (self.max_annotation_size + 2) + self.line)

        # Format the annotations
        annotation_strokes: typing.List[typing.Tuple[int, int, typing.Union[typing.Sequence[int], int, None]]] = []

        # Stroke generation pass
        for index, annotation in enumerate(self.annotations):
            if not annotation.text or not annotation.span:
                continue
            annotation_strokes.append((index, annotation.span[0], annotation.annotation_ansi))
            annotation_strokes.append((index, annotation.span[1], annotation.annotation_ansi))

        # Sort by stroke position, and then annotations so that earlier annotations take priority
        annotation_strokes.sort(key=lambda s: (s[1], s[0]))

        def to_ansi_text(ansi: typing.Union[typing.Sequence[int], int, None]) -> str:
            if ansi is None:
                return "\u001b[0m"
            if isinstance(ansi, int):
                return f"\u001b[0;{ansi}m"
            return f"\u001b[0;{';'.join(str(x) for x in ansi)}m"

        # Now generating the actual lines
        for index, annotation in enumerate(self.annotations):
            if not annotation.text:
                continue

            if use_ansi:
                line = [f"{to_ansi_text(annotation.annotation_ansi)}{annotation.text.rjust(self.max_annotation_size)} {block[0] if annotation.span else ' '}"]
            else:
                line = [f"{annotation.text.rjust(self.max_annotation_size)} {block[0] if annotation.span else ' '}"]

            # Go through each stroke exhaustively
            character_index = 0
            color = annotation.annotation_ansi

            for stroke in annotation_strokes:
                # Skip this if it's an earlier annotation or before the character index
                if stroke[0] < index or stroke[1] < character_index:
                    continue

                if use_ansi and annotation.span and character_index < annotation.span[1] and color != annotation.annotation_ansi:
                    line.append(to_ansi_text(annotation.annotation_ansi))
                    color = annotation.annotation_ansi

                line.append(
                    (
                        " " if not annotation.span else
                        block[0] if character_index < annotation.span[0] else
                        block[2] if character_index < annotation.span[1] else
                        " "
                    )
                    * (stroke[1] - character_index)
                )

                stroke_type = (
                    block[4] if not annotation.span else
                    block[5] if stroke[1] < annotation.span[0] else
                    block[3] if stroke[1] == annotation.span[1] else
                    block[1] if stroke[1] == annotation.span[0] else
                    block[2] if stroke[1] < annotation.span[1] else
                    block[4]
                )

                if use_ansi:
                    target_color = annotation.annotation_ansi if annotation.span and annotation.span[0] < stroke[1] < annotation.span[1] else stroke[2]
                    if target_color != color:
                        line.append(f"{to_ansi_text(target_color)}{stroke_type}")
                        color = target_color
                    else:
                        line.append(stroke_type)
                else:
                    line.append(stroke_type)

                character_index = stroke[1] + 1

            lines.append(''.join(line))

        return "\n".join(lines) + ("\u001b[0m" if use_ansi else "")


class MultilineFormatter:
    """
    A wrapper around LineFormatter that allows annotating a full block of text.
    """
    def __init__(self, text: str):
        self.lines: typing.List[LineFormatter] = [
            LineFormatter(line) for line in text.splitlines()
        ]

    def add_annotation(
        self,
        line: int,
        text: str, span: typing.Optional[typing.Tuple[int, int]],
        annotation_ansi: typing.Union[typing.Sequence[int], int, None] = None,
        text_foreground: typing.Optional[int] = None,
        text_background: typing.Optional[int] = None
    ):
        """
        Add an annotation to a line of this formatter.
        The order in which the annotations are added matters.
        """

        self.lines[line].add_annotation(text, span, annotation_ansi, text_foreground, text_background)

    def output(self, use_complex: bool = True, use_ansi: bool = False) -> str:
        """
        Outputs all lines with their annotations
        """
        max_line = max(formatter.max_annotation_size for formatter in self.lines)

        lines: typing.List[str] = []
        for formatter in self.lines:
            formatter.max_annotation_size = max_line
            lines.append(formatter.output(use_complex, use_ansi))

        return "\n".join(lines)
