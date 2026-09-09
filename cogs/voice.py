import discord
from discord.ext import commands
from discord import app_commands
import json
import os

VOICE_FILE = "voice_config.json"

def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # 1. User Joined a "Join to Create" hub channel
        if after.channel is not None:
            config = load_data(VOICE_FILE)
            g_id = str(member.guild.id)
            j2c_channels = config.get(g_id, {}).get("j2c_channels", [])

            if after.channel.id in j2c_channels:
                category = after.channel.category
                room_name = f"🔊 {member.display_name}'s Room"

                try:
                    temp_channel = await member.guild.create_voice_channel(
                        name=room_name,
                        category=category,
                        user_limit=0
                    )

                    if g_id not in self.temp_channels:
                        self.temp_channels[g_id] = {}
                    self.temp_channels[g_id][temp_channel.id] = member.id

                    await member.move_to(temp_channel)
                except Exception as e:
                    print(f"Error creating Join-to-Create room: {e}")

        # 2. User Left a voice channel — clean up empty temp rooms
        if before.channel is not None:
            g_id = str(member.guild.id)
            if g_id in self.temp_channels and before.channel.id in self.temp_channels[g_id]:
                if len(before.channel.members) == 0:
                    try:
                        del self.temp_channels[g_id][before.channel.id]
                        await before.channel.delete(reason="Temporary Join to Create channel empty")
                    except Exception as e:
                        print(f"Error deleting temp channel: {e}")

    # ==================== SETUP JOIN TO CREATE ====================
    @app_commands.command(name="setup_j2c", description="Create a Join to Create voice hub in your server! ➕")
    @app_commands.default_permissions(administrator=True)
    async def setup_j2c(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        category = await guild.create_category("🔊 TEMP VOICE ROOMS")
        j2c_channel = await category.create_voice_channel("➕ Join to Create")

        config = load_data(VOICE_FILE)
        g_id = str(guild.id)
        if g_id not in config:
            config[g_id] = {}
        if "j2c_channels" not in config[g_id]:
            config[g_id]["j2c_channels"] = []

        config[g_id]["j2c_channels"].append(j2c_channel.id)
        save_data(VOICE_FILE, config)

        embed = discord.Embed(
            title="✅ Join to Create Setup Complete!",
            description=f"Created category **🔊 TEMP VOICE ROOMS** and hub channel {j2c_channel.mention}!\n\n"
                        f"**How it works:** When members join {j2c_channel.mention}, Ariya will automatically create a private temporary voice room for them and move them into it!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

    # ==================== VOICE ROOM MANAGEMENT ====================
    voice_group = app_commands.Group(name="voice", description="Manage your temporary voice channel 🔊")

    @voice_group.command(name="name", description="Rename your temporary voice room")
    @app_commands.describe(new_name="New name for your voice room")
    async def voice_name(self, interaction: discord.Interaction, new_name: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You are not in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        g_id = str(interaction.guild_id)

        if g_id in self.temp_channels and channel.id in self.temp_channels[g_id]:
            owner_id = self.temp_channels[g_id][channel.id]
            if interaction.user.id != owner_id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Only the room owner can rename this channel!", ephemeral=True)
                return

            await channel.edit(name=f"🔊 {new_name}")
            await interaction.response.send_message(f"✅ Renamed room to **🔊 {new_name}**!")
        else:
            await interaction.response.send_message("❌ You are not in an active temporary voice room!", ephemeral=True)

    @voice_group.command(name="lock", description="Lock your temporary voice room")
    async def voice_lock(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You are not in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        g_id = str(interaction.guild_id)

        if g_id in self.temp_channels and channel.id in self.temp_channels[g_id]:
            owner_id = self.temp_channels[g_id][channel.id]
            if interaction.user.id != owner_id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Only the room owner can lock this channel!", ephemeral=True)
                return

            await channel.set_permissions(interaction.guild.default_role, connect=False)
            await interaction.response.send_message("🔒 Your voice room is now **locked**!")
        else:
            await interaction.response.send_message("❌ You are not in an active temporary voice room!", ephemeral=True)

    @voice_group.command(name="unlock", description="Unlock your temporary voice room")
    async def voice_unlock(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You are not in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        g_id = str(interaction.guild_id)

        if g_id in self.temp_channels and channel.id in self.temp_channels[g_id]:
            owner_id = self.temp_channels[g_id][channel.id]
            if interaction.user.id != owner_id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Only the room owner can unlock this channel!", ephemeral=True)
                return

            await channel.set_permissions(interaction.guild.default_role, connect=True)
            await interaction.response.send_message("🔓 Your voice room is now **unlocked**!")
        else:
            await interaction.response.send_message("❌ You are not in an active temporary voice room!", ephemeral=True)

    @voice_group.command(name="limit", description="Set user limit for your temporary voice room")
    @app_commands.describe(limit="User limit (0 to 99)")
    async def voice_limit(self, interaction: discord.Interaction, limit: int):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You are not in a voice channel!", ephemeral=True)
            return

        if limit < 0 or limit > 99:
            await interaction.response.send_message("❌ Limit must be between 0 and 99!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        g_id = str(interaction.guild_id)

        if g_id in self.temp_channels and channel.id in self.temp_channels[g_id]:
            owner_id = self.temp_channels[g_id][channel.id]
            if interaction.user.id != owner_id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Only the room owner can change the user limit!", ephemeral=True)
                return

            await channel.edit(user_limit=limit)
            limit_text = "unlimited" if limit == 0 else f"{limit} members"
            await interaction.response.send_message(f"👥 Set room limit to **{limit_text}**!")
        else:
            await interaction.response.send_message("❌ You are not in an active temporary voice room!", ephemeral=True)


async def setup(bot):
    cog = Voice(bot)
    bot.tree.add_command(cog.voice_group)
    await bot.add_cog(cog)
