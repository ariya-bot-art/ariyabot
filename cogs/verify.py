import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import json
import os

VERIFY_FILE = "verify_config.json"

def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


class VerifyButton(Button):
    def __init__(self):
        super().__init__(
            label="Verify",
            style=discord.ButtonStyle.green,
            emoji="✅",
            custom_id="ariya_verify_button"
        )

    async def callback(self, interaction: discord.Interaction):
        config = load_data(VERIFY_FILE)
        g_id = str(interaction.guild_id)
        role_id = config.get(g_id, {}).get("verify_role")

        if not role_id:
            await interaction.response.send_message("❌ Verification role is not configured for this server!", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ Configured verification role no longer exists!", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("⚠️ You are already verified in this server!", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role, reason="Ariya Verification")
            embed = discord.Embed(
                title="✅ Verification Successful!",
                description=f"Welcome {interaction.user.mention}! You have been granted access to **{interaction.guild.name}**.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to assign role: {e}", ephemeral=True)


class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VerifyView())

    # ==================== VERIFY SLASH COMMAND ====================
    @app_commands.command(name="verify", description="Verify yourself to gain access to the server ✅")
    async def verify(self, interaction: discord.Interaction):
        config = load_data(VERIFY_FILE)
        g_id = str(interaction.guild_id)
        role_id = config.get(g_id, {}).get("verify_role")

        if not role_id:
            await interaction.response.send_message("❌ Verification is not configured for this server! Ask an admin to run `/setup_verify`.", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ Verification role not found!", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("⚠️ You are already verified!", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role, reason="Ariya Slash Verification")
            await interaction.response.send_message(f"✅ Successfully verified! Welcome to **{interaction.guild.name}**!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to verify: {e}", ephemeral=True)

    # ==================== PREFIX .verify COMMAND ====================
    @commands.command(name="verify")
    async def verify_prefix(self, ctx):
        config = load_data(VERIFY_FILE)
        g_id = str(ctx.guild.id)
        role_id = config.get(g_id, {}).get("verify_role")

        if not role_id:
            await ctx.send("❌ Verification is not configured for this server! Ask an admin to run `/setup_verify`.")
            return

        role = ctx.guild.get_role(role_id)
        if not role:
            await ctx.send("❌ Verification role not found!")
            return

        if role in ctx.author.roles:
            await ctx.send(f"⚠️ {ctx.author.mention}, you are already verified!")
            return

        try:
            await ctx.author.add_roles(role, reason="Ariya Prefix Verification")
            await ctx.send(f"✅ {ctx.author.mention} has been successfully verified!")
        except Exception as e:
            await ctx.send(f"❌ Failed to verify: {e}")

    # ==================== SETUP VERIFICATION PANEL ====================
    @app_commands.command(name="setup_verify", description="Set up an interactive Verification Panel in a channel 🛡️")
    @app_commands.describe(role="Role to give verified members", channel="Channel to post verification panel in")
    @app_commands.default_permissions(administrator=True)
    async def setup_verify(self, interaction: discord.Interaction, role: discord.Role, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        config = load_data(VERIFY_FILE)
        g_id = str(interaction.guild_id)

        if g_id not in config:
            config[g_id] = {}

        config[g_id]["verify_role"] = role.id
        config[g_id]["verify_channel"] = target_channel.id
        save_data(VERIFY_FILE, config)

        embed = discord.Embed(
            title="🛡️ Server Verification Required",
            description=f"Welcome to **{interaction.guild.name}**!\n\n"
                        f"Click the green **`✅ Verify`** button below (or type `.verify`) to gain access to the rest of the server.",
            color=discord.Color.green()
        )
        if self.bot.user and self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Role Granted: @{role.name}")

        await target_channel.send(embed=embed, view=VerifyView())
        await interaction.response.send_message(f"✅ Verification panel sent to {target_channel.mention} giving {role.mention} role!")


async def setup(bot):
    await bot.add_cog(Verify(bot))
