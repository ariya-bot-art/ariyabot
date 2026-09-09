import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import timedelta

WARNS_FILE = "warns.json"

def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== KICK ====================
    @app_commands.command(name="kick", description="Kick a member from the server!")
    @app_commands.describe(user="Who to kick", reason="Reason for kick")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ You can't kick someone with equal or higher role!", ephemeral=True)
            return

        try:
            await user.send(f"❌ You have been **kicked** from **{interaction.guild.name}**\nReason: {reason}")
        except:
            pass

        await user.kick(reason=reason)

        embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange())
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    # ==================== BAN ====================
    @app_commands.command(name="ban", description="Ban a member from the server!")
    @app_commands.describe(user="Who to ban", reason="Reason for ban")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ You can't ban someone with equal or higher role!", ephemeral=True)
            return

        try:
            await user.send(f"🔨 You have been **banned** from **{interaction.guild.name}**\nReason: {reason}")
        except:
            pass

        await user.ban(reason=reason)

        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    # ==================== UNBAN ====================
    @app_commands.command(name="unban", description="Unban a user!")
    @app_commands.describe(user_id="The ID of the user to unban")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)

            embed = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green())
            embed.add_field(name="User", value=str(user), inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            await interaction.response.send_message(embed=embed)
        except:
            await interaction.response.send_message("❌ User not found or not banned!", ephemeral=True)

    # ==================== MUTE (TIMEOUT) ====================
    @app_commands.command(name="mute", description="Timeout a member!")
    @app_commands.describe(user="Who to mute", minutes="How many minutes", reason="Reason")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, user: discord.Member, minutes: int = 10, reason: str = "No reason provided"):
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ You can't mute someone with equal or higher role!", ephemeral=True)
            return

        duration = timedelta(minutes=minutes)
        await user.timeout(duration, reason=reason)

        embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.orange())
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Duration", value=f"{minutes} minutes", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    # ==================== UNMUTE ====================
    @app_commands.command(name="unmute", description="Remove timeout from a member!")
    @app_commands.describe(user="Who to unmute")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member):
        await user.timeout(None)

        embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green())
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    # ==================== WARN ====================
    @app_commands.command(name="warn", description="Warn a member!")
    @app_commands.describe(user="Who to warn", reason="Reason for warning")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        warns_data = load_data(WARNS_FILE)
        user_id = str(user.id)

        if user_id not in warns_data:
            warns_data[user_id] = []

        warns_data[user_id].append({
            "reason": reason,
            "moderator": str(interaction.user),
            "date": discord.utils.utcnow().strftime("%Y-%m-%d %H:%M")
        })
        save_data(WARNS_FILE, warns_data)

        try:
            await user.send(f"⚠️ You have been **warned** in **{interaction.guild.name}**\nReason: {reason}")
        except:
            pass

        embed = discord.Embed(title="⚠️ Member Warned", color=discord.Color.yellow())
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=len(warns_data[user_id]), inline=False)
        await interaction.response.send_message(embed=embed)

    # ==================== WARNINGS ====================
    @app_commands.command(name="warnings", description="Check a member's warnings!")
    @app_commands.describe(user="Who to check")
    @app_commands.default_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        warns_data = load_data(WARNS_FILE)
        user_id = str(user.id)

        if user_id not in warns_data or not warns_data[user_id]:
            await interaction.response.send_message(f"✅ {user.mention} has no warnings!")
            return

        embed = discord.Embed(
            title=f"⚠️ Warnings for {user.display_name}",
            color=discord.Color.yellow()
        )
        for i, warn in enumerate(warns_data[user_id], 1):
            embed.add_field(
                name=f"Warning #{i} — {warn['date']}",
                value=f"**Reason:** {warn['reason']}\n**By:** {warn['moderator']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    # ==================== CLEAR WARNINGS ====================
    @app_commands.command(name="clearwarnings", description="Clear all warnings for a member!")
    @app_commands.describe(user="Who to clear warnings for")
    @app_commands.default_permissions(administrator=True)
    async def clearwarnings(self, interaction: discord.Interaction, user: discord.Member):
        warns_data = load_data(WARNS_FILE)
        user_id = str(user.id)
        warns_data[user_id] = []
        save_data(WARNS_FILE, warns_data)
        await interaction.response.send_message(f"✅ Cleared all warnings for {user.mention}")

    # ==================== PURGE ====================
    @app_commands.command(name="purge", description="Delete multiple messages at once!")
    @app_commands.describe(amount="How many messages to delete")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount > 100:
            await interaction.response.send_message("❌ Max 100 messages at once!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ Deleted {len(deleted)} messages!", ephemeral=True)

    # ==================== SLOWMODE ====================
    @app_commands.command(name="slowmode", description="Set slowmode in a channel!")
    @app_commands.describe(seconds="Slowmode delay in seconds (0 to disable)")
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        await interaction.channel.edit(slowmode_delay=seconds)

        if seconds == 0:
            await interaction.response.send_message("✅ Slowmode disabled!")
        else:
            await interaction.response.send_message(f"✅ Slowmode set to {seconds} seconds!")

    # ==================== LOCK/UNLOCK ====================
    @app_commands.command(name="lock", description="Lock a channel!")
    @app_commands.default_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("🔒 Channel locked!")

    @app_commands.command(name="unlock", description="Unlock a channel!")
    @app_commands.default_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message("🔓 Channel unlocked!")

    # ==================== WELCOME SETUP ====================
    @app_commands.command(name="setwelcome", description="Set the welcome channel!")
    @app_commands.describe(channel="Which channel to send welcome messages in")
    @app_commands.default_permissions(administrator=True)
    async def setwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_data("config.json")
        config["welcome_channel"] = channel.id
        save_data("config.json", config)
        await interaction.response.send_message(f"✅ Welcome channel set to {channel.mention}!")

    # ==================== AUTO ROLE SETUP ====================
    @app_commands.command(name="setautorole", description="Set a role to give new members automatically!")
    @app_commands.describe(role="Which role to give new members")
    @app_commands.default_permissions(administrator=True)
    async def setautorole(self, interaction: discord.Interaction, role: discord.Role):
        config = load_data("config.json")
        config["auto_role"] = role.id
        save_data("config.json", config)
        await interaction.response.send_message(f"✅ Auto role set to {role.mention}!")

    # ==================== WELCOME & AUTOROLE EVENTS ====================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = load_data("config.json")

        # Welcome message
        if "welcome_channel" in config:
            channel = self.bot.get_channel(config["welcome_channel"])
            if channel:
                embed = discord.Embed(
                    title=f"👋 Welcome to {member.guild.name}!",
                    description=f"Hey {member.mention}, welcome to the server! We're glad to have you here 🎉",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"Member #{member.guild.member_count}")
                await channel.send(embed=embed)

        # Auto role
        if "auto_role" in config:
            role = member.guild.get_role(config["auto_role"])
            if role:
                await member.add_roles(role)


async def setup(bot):
    await bot.add_cog(Moderation(bot))