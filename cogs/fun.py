import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
from dotenv import load_dotenv
import random
import os

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== SHIP METER ====================
    @app_commands.command(name="ship", description="Check compatibility between two members 💘")
    @app_commands.describe(user1="First person", user2="Second person")
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
        await interaction.response.defer()

        score = random.randint(0, 100)

        if score < 20:
            label = "💀 Absolutely Not"
            color = discord.Color.red()
        elif score < 40:
            label = "😬 Unlikely"
            color = discord.Color.orange()
        elif score < 60:
            label = "🤔 Maybe..."
            color = discord.Color.yellow()
        elif score < 80:
            label = "😍 Pretty Good!"
            color = discord.Color.green()
        else:
            label = "💞 Soulmates!"
            color = discord.Color.magenta()

        # Generate AI ship name
        prompt = f"Create a fun couple ship name by combining '{user1.display_name}' and '{user2.display_name}'. Just give the ship name, nothing else."
        response = model.generate_content(prompt)
        ship_name = response.text.strip()

        bar = "█" * (score // 10) + "░" * (10 - score // 10)

        embed = discord.Embed(
            title=f"💘 Ship Meter",
            color=color
        )
        embed.add_field(name="Couple", value=f"{user1.mention} & {user2.mention}", inline=False)
        embed.add_field(name="Ship Name", value=f"**{ship_name}**", inline=False)
        embed.add_field(name="Compatibility", value=f"`{bar}` {score}%", inline=False)
        embed.add_field(name="Verdict", value=label, inline=False)
        await interaction.followup.send(embed=embed)

    # ==================== FAKE DRAMA GENERATOR ====================
    @app_commands.command(name="drama", description="Generate fake drama between two members 👀")
    @app_commands.describe(user1="First person", user2="Second person")
    async def drama(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
        await interaction.response.defer()

        prompt = f"""Create a funny fake drama story between {user1.display_name} and {user2.display_name} in a Discord server. 
Make it dramatic, funny and obviously fake. Keep it under 150 words. No real insults."""

        response = model.generate_content(prompt)

        embed = discord.Embed(
            title="🍿 BREAKING DRAMA",
            description=response.text,
            color=discord.Color.red()
        )
        embed.set_footer(text="⚠️ This is 100% fake and for fun only!")
        await interaction.followup.send(embed=embed)

    # ==================== ROAST ====================
    @app_commands.command(name="roast", description="Get roasted by AI 🔥")
    @app_commands.describe(user="Who to roast?")
    async def roast(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()

        prompt = f"""Give a funny, lighthearted roast of a Discord user named {user.display_name}. 
Keep it playful and not genuinely mean. Max 2-3 sentences."""

        response = model.generate_content(prompt)

        embed = discord.Embed(
            title=f"🔥 Roasting {user.display_name}",
            description=response.text,
            color=discord.Color.orange()
        )
        embed.set_footer(text="All in good fun! 😄")
        await interaction.followup.send(embed=embed)

    # ==================== TRIVIA ====================
    @app_commands.command(name="trivia", description="Get a random trivia question!")
    async def trivia(self, interaction: discord.Interaction):
        await interaction.response.defer()

        categories = ["science", "history", "gaming", "movies", "music", "sports", "technology"]
        category = random.choice(categories)

        prompt = f"""Give me a fun trivia question about {category}.
Format exactly like this:
Question: [question]
Answer: [answer]
Fun Fact: [one interesting related fact]"""

        response = model.generate_content(prompt)
        result = response.text

        embed = discord.Embed(
            title=f"🧠 Trivia Time! — {category.capitalize()}",
            description=result,
            color=discord.Color.gold()
        )
        embed.set_footer(text="Reply with your answer!")
        await interaction.followup.send(embed=embed)

    # ==================== 8BALL ====================
    @app_commands.command(name="8ball", description="Ask the magic 8ball a question!")
    @app_commands.describe(question="What's your question?")
    async def eightball(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()

        prompt = f"""You are a magic 8ball. Answer this question in a mysterious, dramatic way in 1-2 sentences: '{question}'"""
        response = model.generate_content(prompt)

        embed = discord.Embed(
            title="🎱 Magic 8Ball",
            color=discord.Color.dark_blue()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response.text, inline=False)
        await interaction.followup.send(embed=embed)

    # ==================== MEME GENERATOR ====================
    @app_commands.command(name="meme", description="Get an AI generated meme idea!")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()

        prompt = """Create a funny meme idea. Format like this:
Template: [popular meme template name]
Top text: [top text]
Bottom text: [bottom text]
Why it's funny: [one sentence explanation]"""

        response = model.generate_content(prompt)

        embed = discord.Embed(
            title="😂 Meme Generator",
            description=response.text,
            color=discord.Color.yellow()
        )
        await interaction.followup.send(embed=embed)

    # ==================== CONFESSION ====================
    @app_commands.command(name="confess", description="Submit an anonymous confession 🤫")
    @app_commands.describe(confession="Your anonymous confession")
    async def confess(self, interaction: discord.Interaction, confession: str):
        await interaction.response.send_message("✅ Your confession has been submitted anonymously!", ephemeral=True)

        embed = discord.Embed(
            title="🤫 Anonymous Confession",
            description=confession,
            color=discord.Color.greyple()
        )
        embed.set_footer(text="Submitted anonymously")
        await interaction.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Fun(bot))