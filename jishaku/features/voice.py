# -*- coding: utf-8 -*-

"""
jishaku.features.voice
~~~~~~~~~~~~~~~~~~~~~~~

The jishaku core voice-related commands.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import typing

import discord
import discord.opus
import discord.voice_client

from jishaku.features.baseclass import Feature
from jishaku.types import ContextA


class VoiceFeature(Feature):
    """
    Feature containing the core voice-related commands
    """

    @staticmethod
    async def voice_check(ctx: ContextA):
        """
        Check for whether VC is available in this bot.
        """

        if not discord.voice_client.has_nacl:
            return await ctx.send("Voice cannot be used because PyNaCl is not loaded.")

        if not discord.opus.is_loaded():
            if hasattr(discord.opus, '_load_default'):
                if not discord.opus._load_default():  # type: ignore  # pylint: disable=protected-access,no-member
                    return await ctx.send(
                        "Voice cannot be used because libopus is not loaded and attempting to load the default failed."
                    )
            else:
                return await ctx.send("Voice cannot be used because libopus is not loaded.")

    @staticmethod
    async def connected_check(ctx: ContextA):
        """
        Check whether we are connected to VC in this guild.
        """

        if not ctx.guild or not ctx.guild.voice_client or (
            not ctx.guild.voice_client.is_connected()
            if isinstance(ctx.guild.voice_client, discord.VoiceClient)
            else False
        ):
            return await ctx.send("Not connected to a voice channel in this guild.")

    @staticmethod
    async def playing_check(ctx: ContextA):
        """
        Checks whether we are playing audio in VC in this guild.

        This doubles up as a connection check.
        """

        check = await VoiceFeature.connected_check(ctx)
        if check:
            return check

        guild: discord.Guild = ctx.guild  # type: ignore

        if (not guild.voice_client.is_playing() if isinstance(guild.voice_client, discord.VoiceClient) else False):
            return await ctx.send("The voice client in this guild is not playing anything.")

    @Feature.Command(parent="jsk", name="voice", aliases=["vc"],
                     invoke_without_command=True, ignore_extra=False)
    async def jsk_voice(self, ctx: ContextA):
        """
        Voice-related commands.

        If invoked without subcommand, relays current voice state.
        """

        if await self.voice_check(ctx):
            return

        guild: discord.Guild = ctx.guild  # type: ignore

        # give info about the current voice client if there is one
        voice: discord.VoiceProtocol = guild.voice_client  # type: ignore

        if isinstance(voice, discord.VoiceClient):
            if not voice or not voice.is_connected():
                return await ctx.send("Not connected.")

            await ctx.send(f"Connected to {voice.channel.name}, "
                           f"{'paused' if voice.is_paused() else 'playing' if voice.is_playing() else 'idle'}.")
        else:
            await ctx.send(f"Connected to {voice.channel} with a custom VoiceProtocol: {voice}")

    @Feature.Command(parent="jsk_voice", name="join", aliases=["connect"])
    async def jsk_vc_join(
        self,
        ctx: ContextA,
        *,
        destination: typing.Union[discord.VoiceChannel, discord.Member] = None  # type: ignore
    ):
        """
        Joins a voice channel, or moves to it if already connected.

        Passing a voice channel uses that voice channel.
        Passing a member will use that member's current voice channel.
        Passing nothing will use the author's voice channel.
        """

        if await self.voice_check(ctx):
            return

        destination = destination or ctx.author

        if isinstance(destination, discord.Member):
            if destination.voice and destination.voice.channel:
                if isinstance(destination.voice.channel, discord.StageChannel):
                    return await ctx.send("Cannot join a stage channel.")
                destination = destination.voice.channel
            else:
                return await ctx.send("Member has no voice channel.")

        voice: discord.VoiceProtocol = ctx.guild.voice_client  # type: ignore

        if voice:
            if isinstance(voice, discord.VoiceClient):
                await voice.move_to(destination)
            else:
                await ctx.send(f"Can't move a custom VoiceProtocol: {voice}")
        else:
            await destination.connect(reconnect=True)

        await ctx.send(f"Connected to {destination.name}.")

    @Feature.Command(parent="jsk_voice", name="disconnect", aliases=["dc"])
    async def jsk_vc_disconnect(self, ctx: ContextA):
        """
        Disconnects from the voice channel in this guild, if there is one.
        """

        if await self.connected_check(ctx):
            return

        voice: discord.VoiceProtocol = ctx.guild.voice_client  # type: ignore

        if isinstance(voice, discord.VoiceClient):
            await voice.disconnect()
            await ctx.send(f"Disconnected from {voice.channel.name}.")
        else:
            await ctx.send(f"Can't disconnect a custom VoiceProtocol: {voice}")

    @Feature.Command(parent="jsk_voice", name="stop")
    async def jsk_vc_stop(self, ctx: ContextA):
        """
        Stops running an audio source, if there is one.
        """

        if await self.playing_check(ctx):
            return

        voice: discord.VoiceProtocol = ctx.guild.voice_client  # type: ignore

        if isinstance(voice, discord.VoiceClient):
            voice.stop()
            await ctx.send(f"Stopped playing audio in {voice.channel.name}.")
        else:
            await ctx.send(f"Can't stop a custom VoiceProtocol: {voice}")

    @Feature.Command(parent="jsk_voice", name="pause")
    async def jsk_vc_pause(self, ctx: ContextA):
        """
        Pauses a running audio source, if there is one.
        """

        if await self.playing_check(ctx):
            return

        voice: discord.VoiceProtocol = ctx.guild.voice_client  # type: ignore

        if isinstance(voice, discord.VoiceClient):
            if voice.is_paused():
                return await ctx.send("Audio is already paused.")

            voice.pause()
            await ctx.send(f"Paused audio in {voice.channel.name}.")
        else:
            await ctx.send(f"Can't pause a custom VoiceProtocol: {voice}")

    @Feature.Command(parent="jsk_voice", name="resume")
    async def jsk_vc_resume(self, ctx: ContextA):
        """
        Resumes a running audio source, if there is one.
        """

        if await self.connected_check(ctx):
            return

        voice: discord.VoiceProtocol = ctx.guild.voice_client  # type: ignore

        if isinstance(voice, discord.VoiceClient):
            if not voice.is_paused():
                return await ctx.send("Audio is not paused.")

            voice.resume()
            await ctx.send(f"Resumed audio in {voice.channel.name}.")
        else:
            await ctx.send(f"Can't resume a custom VoiceProtocol: {voice}")

    @Feature.Command(parent="jsk_voice", name="volume")
    async def jsk_vc_volume(self, ctx: ContextA, *, percentage: float):
        """
        Adjusts the volume of an audio source if it is supported.
        """

        if await self.playing_check(ctx):
            return

        volume = max(0.0, min(1.0, percentage / 100))

        voice: discord.VoiceProtocol = ctx.guild.voice_client  # type: ignore

        if isinstance(voice, discord.VoiceClient):
            source = voice.source

            if not isinstance(source, discord.PCMVolumeTransformer):
                return await ctx.send("This source doesn't support adjusting volume or "
                                      "the interface to do so is not exposed.")

            source.volume = volume

            await ctx.send(f"Volume set to {volume * 100:.2f}%")
        else:
            await ctx.send(f"Can't transform a custom VoiceProtocol: {voice}")

    @Feature.Command(parent="jsk_voice", name="play", aliases=["play_local"])
    async def jsk_vc_play(self, ctx: ContextA, *, uri: str):
        """
        Plays audio direct from a URI.

        Can be either a local file or an audio resource on the internet.
        """

        if await self.connected_check(ctx):
            return

        voice: discord.VoiceProtocol = ctx.guild.voice_client  # type: ignore

        if isinstance(voice, discord.VoiceClient):
            if voice.is_playing():
                voice.stop()

            # remove embed maskers if present
            uri = uri.lstrip("<").rstrip(">")

            voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(uri)))
            await ctx.send(f"Playing in {voice.channel.name}.")
        else:
            await ctx.send(f"Can't play on a custom VoiceProtocol: {voice}")
