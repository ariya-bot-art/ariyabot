import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time

SECURITY_FILE = "security_config.json"

def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_actions = {}
        self.role_actions = {}
        self.ban_actions = {}

    def is_whitelisted(self, guild_id: int, user_id: int, owner_id: int) -> bool:
        if user_id == owner_id or user_id == self.bot.user.id:
            return True
        config = load_data(SECURITY_FILE)
        guild_whitelist = config.get(str(guild_id), {}).get("whitelist", [])
        return str(user_id) in guild_whitelist

    def is_enabled(self, guild_id: int) -> bool:
        config = load_data(SECURITY_FILE)
        return config.get(str(guild_id), {}).get("enabled", True)

    async def punish_attacker(self, guild: discord.Guild, user: discord.User, reason: str):
        try:
            await guild.ban(user, reason=f"🛡️ Ariya Anti-Nuke: {reason}")
            
            embed = discord.Embed(
                title="🚨 ANTI-NUKE SYSTEM TRIGGERED",
                description=f"**Attacker:** {user.mention} (`{user.id}`)\n"
                            f"**Reason:** {reason}\n"
                            f"**Action Taken:** 🔨 Banned from server!",
                color=discord.Color.red()
            )
            embed.set_footer(text="Ariya Anti-Nuke Security • Server Protected")
            
            channel = guild.system_channel or guild.text_channels[0]
            if channel:
                await channel.send(embed=embed)
        except Exception as e:
            print(f"Failed to punish attacker {user.id}: {e}")

    # ==================== ANTI CHANNEL CREATION / DELETION ====================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        await self.handle_channel_action(channel.guild, discord.AuditLogAction.channel_create, "Mass Channel Creation")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self.handle_channel_action(channel.guild, discord.AuditLogAction.channel_delete, "Mass Channel Deletion")

    async def handle_channel_action(self, guild: discord.Guild, action_type, reason_prefix: str):
        if not self.is_enabled(guild.id):
            return

        try:
            async for entry in guild.audit_logs(limit=1, action=action_type):
                executor = entry.user
                if not executor or (executor.bot and executor.id == self.bot.user.id):
                    return

                if self.is_whitelisted(guild.id, executor.id, guild.owner_id):
                    return

                now = time.time()
                g_id = str(guild.id)
                u_id = str(executor.id)

                if g_id not in self.channel_actions:
                    self.channel_actions[g_id] = {}
                if u_id not in self.channel_actions[g_id]:
                    self.channel_actions[g_id][u_id] = []

                self.channel_actions[g_id][u_id] = [t for t in self.channel_actions[g_id][u_id] if now - t < 10]
                self.channel_actions[g_id][u_id].append(now)

                if len(self.channel_actions[g_id][u_id]) >= 3:
                    await self.punish_attacker(guild, executor, f"{reason_prefix} (>3 in 10s)")
                    self.channel_actions[g_id][u_id].clear()
        except Exception as e:
            print(f"Anti-Nuke channel error: {e}")

    # ==================== ANTI ROLE CREATION / DELETION ====================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        await self.handle_role_action(role.guild, discord.AuditLogAction.role_create, "Mass Role Creation")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self.handle_role_action(role.guild, discord.AuditLogAction.role_delete, "Mass Role Deletion")

    async def handle_role_action(self, guild: discord.Guild, action_type, reason_prefix: str):
        if not self.is_enabled(guild.id):
            return

        try:
            async for entry in guild.audit_logs(limit=1, action=action_type):
                executor = entry.user
                if not executor or (executor.bot and executor.id == self.bot.user.id):
                    return

                if self.is_whitelisted(guild.id, executor.id, guild.owner_id):
                    return

                now = time.time()
                g_id = str(guild.id)
                u_id = str(executor.id)

                if g_id not in self.role_actions:
                    self.role_actions[g_id] = {}
                if u_id not in self.role_actions[g_id]:
                    self.role_actions[g_id][u_id] = []

                self.role_actions[g_id][u_id] = [t for t in self.role_actions[g_id][u_id] if now - t < 10]
                self.role_actions[g_id][u_id].append(now)

                if len(self.role_actions[g_id][u_id]) >= 3:
                    await self.punish_attacker(guild, executor, f"{reason_prefix} (>3 in 10s)")
                    self.role_actions[g_id][u_id].clear()
        except Exception as e:
            print(f"Anti-Nuke role error: {e}")

    # ==================== ANTI MASS BAN ====================
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        if not self.is_enabled(guild.id):
            return

        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                executor = entry.user
                if not executor or executor.id == self.bot.user.id:
                    return

                if self.is_whitelisted(guild.id, executor.id, guild.owner_id):
                    return

                now = time.time()
                g_id = str(guild.id)
                u_id = str(executor.id)

                if g_id not in self.ban_actions:
                    self.ban_actions[g_id] = {}
                if u_id not in self.ban_actions[g_id]:
                    self.ban_actions[g_id][u_id] = []

                self.ban_actions[g_id][u_id] = [t for t in self.ban_actions[g_id][u_id] if now - t < 10]
                self.ban_actions[g_id][u_id].append(now)

                if len(self.ban_actions[g_id][u_id]) >= 3:
                    await self.punish_attacker(guild, executor, "Mass Member Banning (>3 in 10s)")
                    self.ban_actions[g_id][u_id].clear()
        except Exception as e:
            print(f"Anti-Nuke ban error: {e}")

    # ==================== SLASH COMMANDS ====================
    antinuke_group = app_commands.Group(name="antinuke", description="Manage Ariya Anti-Nuke protection settings 🛡️")

    @antinuke_group.command(name="status", description="Check Anti-Nuke status for this server")
    async def antinuke_status(self, interaction: discord.Interaction):
        enabled = self.is_enabled(interaction.guild_id)
        config = load_data(SECURITY_FILE)
        whitelist = config.get(str(interaction.guild_id), {}).get("whitelist", [])

        embed = discord.Embed(
            title="🛡️ Ariya Anti-Nuke Protection Status",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        embed.add_field(name="Status", value="`🟢 ENABLED`" if enabled else "`🔴 DISABLED`", inline=True)
        embed.add_field(name="Protection Scope", value="Channels, Roles, Mass Bans", inline=True)
        embed.add_field(name="Trigger Threshold", value="> 3 actions in 10s", inline=True)
        embed.add_field(name="Whitelisted Users/Bots", value=f"`{len(whitelist)}` users/bots", inline=False)
        embed.set_footer(text="Server Owner & Ariya Bot are automatically whitelisted")
        
        await interaction.response.send_message(embed=embed)

    @antinuke_group.command(name="toggle", description="Enable or disable Anti-Nuke protection")
    @app_commands.describe(enable="Turn Anti-Nuke ON or OFF")
    @app_commands.default_permissions(administrator=True)
    async def antinuke_toggle(self, interaction: discord.Interaction, enable: bool):
        config = load_data(SECURITY_FILE)
        g_id = str(interaction.guild_id)
        if g_id not in config:
            config[g_id] = {}
        config[g_id]["enabled"] = enable
        save_data(SECURITY_FILE, config)

        status_text = "enabled 🟢" if enable else "disabled 🔴"
        await interaction.response.send_message(f"✅ Anti-Nuke security has been **{status_text}** for this server!")

    @antinuke_group.command(name="whitelist_add", description="Add a user or bot to Anti-Nuke whitelist")
    @app_commands.describe(user="User or bot to whitelist")
    @app_commands.default_permissions(administrator=True)
    async def antinuke_whitelist_add(self, interaction: discord.Interaction, user: discord.User):
        config = load_data(SECURITY_FILE)
        g_id = str(interaction.guild_id)
        if g_id not in config:
            config[g_id] = {}
        if "whitelist" not in config[g_id]:
            config[g_id]["whitelist"] = []

        u_id = str(user.id)
        if u_id in config[g_id]["whitelist"]:
            await interaction.response.send_message(f"⚠️ {user.mention} is already on the Anti-Nuke whitelist!", ephemeral=True)
            return

        config[g_id]["whitelist"].append(u_id)
        save_data(SECURITY_FILE, config)
        await interaction.response.send_message(f"✅ Added {user.mention} to the Anti-Nuke whitelist!")

    @antinuke_group.command(name="whitelist_remove", description="Remove a user or bot from Anti-Nuke whitelist")
    @app_commands.describe(user="User or bot to remove from whitelist")
    @app_commands.default_permissions(administrator=True)
    async def antinuke_whitelist_remove(self, interaction: discord.Interaction, user: discord.User):
        config = load_data(SECURITY_FILE)
        g_id = str(interaction.guild_id)
        whitelist = config.get(g_id, {}).get("whitelist", [])

        u_id = str(user.id)
        if u_id not in whitelist:
            await interaction.response.send_message(f"⚠️ {user.mention} is not in the whitelist!", ephemeral=True)
            return

        whitelist.remove(u_id)
        config[g_id]["whitelist"] = whitelist
        save_data(SECURITY_FILE, config)
        await interaction.response.send_message(f"✅ Removed {user.mention} from the Anti-Nuke whitelist!")


async def setup(bot):
    cog = Security(bot)
    bot.tree.add_command(cog.antinuke_group)
    await bot.add_cog(cog)
