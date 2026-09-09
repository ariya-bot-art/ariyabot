import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
from dotenv import load_dotenv
import json
import os
import random
from datetime import datetime, timedelta

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# Storage files
CHALLENGES_FILE = "challenges.json"
ECONOMY_FILE = "economy.json"

def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

class Challenges(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_challenge = None
        self.challenge_end = None

    # ==================== GENERATE DAILY CHALLENGE ====================
    @app_commands.command(name="challenge", description="View today's daily challenge!")
    async def challenge(self, interaction: discord.Interaction):
        await interaction.response.defer()

        challenges_data = load_data(CHALLENGES_FILE)
        today = datetime.now().strftime("%Y-%m-%d")

        # Generate new challenge if none exists for today
        if challenges_data.get("date") != today:
            categories = [
                "creative writing", "trivia", "riddle",
                "would you rather", "this or that", "debate topic",
                "fun fact challenge", "word game"
            ]
            category = random.choice(categories)

            prompt = f"""Create a fun Discord server daily challenge for the category: {category}
Format exactly like this:
Title: [challenge title]
Category: {category}
Description: [clear challenge description, 2-3 sentences]
How to participate: [simple instructions]
Reward: [coin reward between 50-200]coins"""

            response = model.generate_content(prompt)
            result = response.text

            # Extract reward
            reward = 100  # default
            for line in result.split("\n"):
                if "Reward:" in line:
                    try:
                        reward = int(''.join(filter(str.isdigit, line)))
                    except:
                        reward = 100

            challenges_data = {
                "date": today,
                "challenge": result,
                "reward": reward,
                "participants": []
            }
            save_data(CHALLENGES_FILE, challenges_data)

        embed = discord.Embed(
            title="🎯 Daily Challenge",
            description=challenges_data["challenge"],
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"📅 {today} • Complete with /complete")
        await interaction.followup.send(embed=embed)

    # ==================== COMPLETE CHALLENGE ====================
    @app_commands.command(name="complete", description="Submit your daily challenge completion!")
    @app_commands.describe(submission="Your challenge submission or answer")
    async def complete(self, interaction: discord.Interaction, submission: str):
        await interaction.response.defer()

        challenges_data = load_data(CHALLENGES_FILE)
        economy_data = load_data(ECONOMY_FILE)
        today = datetime.now().strftime("%Y-%m-%d")
        user_id = str(interaction.user.id)

        if challenges_data.get("date") != today:
            await interaction.followup.send("❌ No active challenge today! Use `/challenge` first.")
            return

        if user_id in challenges_data.get("participants", []):
            await interaction.followup.send("❌ You already completed today's challenge!")
            return

        # Give reward
        reward = challenges_data.get("reward", 100)
        if user_id not in economy_data:
            economy_data[user_id] = {"coins": 0, "total_earned": 0}

        economy_data[user_id]["coins"] += reward
        economy_data[user_id]["total_earned"] = economy_data[user_id].get("total_earned", 0) + reward
        challenges_data["participants"].append(user_id)

        save_data(ECONOMY_FILE, economy_data)
        save_data(CHALLENGES_FILE, challenges_data)

        embed = discord.Embed(
            title="✅ Challenge Completed!",
            color=discord.Color.green()
        )
        embed.add_field(name="Your Submission", value=submission, inline=False)
        embed.add_field(name="Reward", value=f"🪙 +{reward} coins", inline=False)
        embed.add_field(name="New Balance", value=f"🪙 {economy_data[user_id]['coins']} coins", inline=False)
        embed.set_footer(text=f"Completed by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    # ==================== LEADERBOARD ====================
    @app_commands.command(name="leaderboard", description="View the server coin leaderboard!")
    async def leaderboard(self, interaction: discord.Interaction):
        economy_data = load_data(ECONOMY_FILE)

        if not economy_data:
            await interaction.response.send_message("❌ No data yet! Complete some challenges first.")
            return

        # Sort by coins
        sorted_users = sorted(economy_data.items(), key=lambda x: x[1]["coins"], reverse=True)[:10]

        embed = discord.Embed(
            title="🏆 Coin Leaderboard",
            color=discord.Color.gold()
        )

        medals = ["🥇", "🥈", "🥉"]
        description = ""

        for i, (user_id, data) in enumerate(sorted_users):
            try:
                user = await self.bot.fetch_user(int(user_id))
                name = user.display_name
            except:
                name = "Unknown User"

            medal = medals[i] if i < 3 else f"`#{i+1}`"
            description += f"{medal} **{name}** — 🪙 {data['coins']} coins\n"

        embed.description = description
        await interaction.response.send_message(embed=embed)

    # ==================== CHECK BALANCE ====================
    @app_commands.command(name="balance", description="Check your coin balance!")
    async def balance(self, interaction: discord.Interaction):
        economy_data = load_data(ECONOMY_FILE)
        user_id = str(interaction.user.id)

        if user_id not in economy_data:
            await interaction.response.send_message("❌ You have no coins yet! Complete a challenge to earn some.")
            return

        data = economy_data[user_id]
        embed = discord.Embed(
            title=f"🪙 {interaction.user.display_name}'s Balance",
            color=discord.Color.gold()
        )
        embed.add_field(name="Current Coins", value=f"🪙 {data['coins']}", inline=True)
        embed.add_field(name="Total Earned", value=f"🪙 {data.get('total_earned', 0)}", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Challenges(bot))