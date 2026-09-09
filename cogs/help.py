import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="See all Ariya commands!")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✨ Ariya — Command List",
            description="Your all-in-one AI companion powered by Gemini!",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="🤖 AI",
            value="`/chat` `/clearchat` `/vibe`",
            inline=False
        )
        embed.add_field(
            name="🎵 Music",
            value="`/play` `/pause` `/resume` `/skip` `/stop` `/queue` `/leave`",
            inline=False
        )
        embed.add_field(
            name="😂 Fun",
            value="`/ship` `/drama` `/roast` `/trivia` `/8ball` `/meme` `/confess`",
            inline=False
        )
        embed.add_field(
            name="🎯 Daily Challenges",
            value="`/challenge` `/complete` `/leaderboard` `/balance`",
            inline=False
        )
        embed.add_field(
            name="🛠️ Utility",
            value="`/schedule` `/newspaper` `/summarize` `/poll` `/give` `/userinfo` `/serverinfo`",
            inline=False
        )
        embed.add_field(
            name="🔨 Moderation",
            value="`/kick` `/ban` `/unban` `/mute` `/unmute` `/warn` `/warnings` `/clearwarnings` `/purge` `/slowmode` `/lock` `/unlock` `/setwelcome` `/setautorole`",
            inline=False
        )
        embed.set_footer(text="Ariya Bot • Powered by Gemini AI")
        if self.bot.user and self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))