import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, search: str, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))

        if 'entries' in data and len(data['entries']) > 0:
            data = data['entries'][0]

        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}

    def play_next(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if guild_id in self.queues and len(self.queues[guild_id]) > 0:
            next_song = self.queues[guild_id].pop(0)
            voice_client = interaction.guild.voice_client
            if voice_client and voice_client.is_connected():
                voice_client.play(
                    next_song['source'],
                    after=lambda e: self.play_next(interaction)
                )
                asyncio.run_coroutine_threadsafe(
                    interaction.channel.send(f"🎵 Now playing: **{next_song['title']}**"),
                    self.bot.loop
                )

    # ==================== PLAY ====================
    @app_commands.command(name="play", description="Play music from YouTube in your voice channel 🎵")
    @app_commands.describe(query="Song title or YouTube URL")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel to use this command!", ephemeral=True)
            return

        await interaction.response.defer()

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)

        try:
            player = await YTDLSource.from_url(query, loop=self.bot.loop)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to fetch song: {e}")
            return

        guild_id = interaction.guild_id
        if guild_id not in self.queues:
            self.queues[guild_id] = []

        if voice_client.is_playing() or voice_client.is_paused():
            self.queues[guild_id].append({'title': player.title, 'source': player})
            embed = discord.Embed(
                title="🎶 Added to Queue",
                description=f"**{player.title}**",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Position #{len(self.queues[guild_id])} in queue")
            await interaction.followup.send(embed=embed)
        else:
            voice_client.play(player, after=lambda e: self.play_next(interaction))
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**{player.title}**",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)

    # ==================== PAUSE ====================
    @app_commands.command(name="pause", description="Pause currently playing music")
    async def pause(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("⏸️ Music paused!")
        else:
            await interaction.response.send_message("❌ No music is currently playing!", ephemeral=True)

    # ==================== RESUME ====================
    @app_commands.command(name="resume", description="Resume paused music")
    async def resume(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("▶️ Music resumed!")
        else:
            await interaction.response.send_message("❌ Music is not paused!", ephemeral=True)

    # ==================== SKIP ====================
    @app_commands.command(name="skip", description="Skip to the next song in queue")
    async def skip(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped current song!")
        else:
            await interaction.response.send_message("❌ Nothing is playing right now!", ephemeral=True)

    # ==================== STOP ====================
    @app_commands.command(name="stop", description="Stop music and clear queue")
    async def stop(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if guild_id in self.queues:
            self.queues[guild_id].clear()

        voice_client = interaction.guild.voice_client
        if voice_client:
            voice_client.stop()
            await voice_client.disconnect()
            await interaction.response.send_message("⏹️ Music stopped and queue cleared!")
        else:
            await interaction.response.send_message("❌ Bot is not connected to a voice channel!", ephemeral=True)

    # ==================== LEAVE ====================
    @app_commands.command(name="leave", description="Disconnect bot from voice channel")
    async def leave(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.disconnect()
            await interaction.response.send_message("👋 Disconnected from voice channel!")
        else:
            await interaction.response.send_message("❌ Bot is not in a voice channel!", ephemeral=True)

    # ==================== QUEUE ====================
    @app_commands.command(name="queue", description="View current song queue")
    async def queue(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        queue_list = self.queues.get(guild_id, [])

        if not queue_list:
            await interaction.response.send_message("🎶 Queue is currently empty!")
            return

        description = ""
        for i, item in enumerate(queue_list, 1):
            description += f"`#{i}` **{item['title']}**\n"

        embed = discord.Embed(
            title="🎶 Song Queue",
            description=description,
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Total: {len(queue_list)} songs in queue")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Music(bot))
