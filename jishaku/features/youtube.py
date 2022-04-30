# -*- coding: utf-8 -*-

"""
jishaku.features.youtube
~~~~~~~~~~~~~~~~~~~~~~~~~

The jishaku youtube-dl command.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import typing

import discord

from jishaku.types import ContextA

try:
    import yt_dlp as youtube_dl  # type: ignore
except ImportError:
    import youtube_dl  # type: ignore

from jishaku.features.baseclass import Feature
from jishaku.features.voice import VoiceFeature

BASIC_OPTS = {
    'format': 'webm[abr>0]/bestaudio/best',
    'prefer_ffmpeg': True,
    'quiet': True
}


class BasicYouTubeDLSource(discord.FFmpegPCMAudio):
    """
    Basic audio source for youtube_dl-compatible URLs.
    """

    def __init__(self, url: str, download: bool = False):
        ytdl = youtube_dl.YoutubeDL(BASIC_OPTS)
        info: typing.Dict[str, typing.Any] = ytdl.extract_info(url, download=download)  # type: ignore
        super().__init__(info['url'])


class YouTubeFeature(Feature):
    """
    Feature containing the youtube-dl command
    """

    @Feature.Command(parent="jsk_voice", name="youtube_dl", aliases=["youtubedl", "ytdl", "yt"])
    async def jsk_vc_youtube_dl(self, ctx: ContextA, *, url: str):
        """
        Plays audio from youtube_dl-compatible sources.
        """

        if await VoiceFeature.connected_check(ctx):
            return

        voice: discord.VoiceProtocol = ctx.guild.voice_client  # type: ignore

        if isinstance(voice, discord.VoiceClient):
            if voice.is_playing():
                voice.stop()

            # remove embed maskers if present
            url = url.lstrip("<").rstrip(">")

            voice.play(discord.PCMVolumeTransformer(BasicYouTubeDLSource(url)))
            await ctx.send(f"Playing in {voice.channel.name}.")
        else:
            await ctx.send(f"Can't play on a custom VoiceProtocol: {voice}")
