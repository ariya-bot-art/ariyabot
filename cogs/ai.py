import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# Store conversation history per user
chat_histories = {}

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== AI CHAT COMPANION ====================
    @app_commands.command(name="chat", description="Chat with the AI companion!")
    @app_commands.describe(message="What do you want to say?")
    async def chat(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer()

        user_id = str(interaction.user.id)

        # Create history for new users
        if user_id not in chat_histories:
            chat_histories[user_id] = []

        # Add user message to history
        chat_histories[user_id].append({
            "role": "user",
            "parts": [message]
        })

        try:
            chat = model.start_chat(history=chat_histories[user_id][:-1])
            response = chat.send_message(message)
            reply = response.text

            # Add bot response to history
            chat_histories[user_id].append({
                "role": "model",
                "parts": [reply]
            })

            # Keep history limited to last 20 messages
            if len(chat_histories[user_id]) > 20:
                chat_histories[user_id] = chat_histories[user_id][-20:]

            embed = discord.Embed(
                title="🤖 AI Companion",
                description=reply,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Talking to {interaction.user.name}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    # ==================== CLEAR CHAT HISTORY ====================
    @app_commands.command(name="clearchat", description="Clear your AI chat history")
    async def clearchat(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id in chat_histories:
            chat_histories.pop(user_id)
        await interaction.response.send_message("✅ Your chat history has been cleared!")

    # ==================== VIBE CHECKER ====================
    @app_commands.command(name="vibe", description="Check the vibe of this channel!")
    async def vibe(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Grab last 20 messages from channel
        messages = []
        async for msg in interaction.channel.history(limit=20):
            if not msg.author.bot:
                messages.append(f"{msg.author.name}: {msg.content}")

        if not messages:
            await interaction.followup.send("❌ No messages found to analyze!")
            return

        chat_log = "\n".join(reversed(messages))

        prompt = f"""Analyze the vibe of this Discord chat and give:
1. A vibe score out of 100
2. A vibe label (e.g. Chaotic, Chill, Toxic, Wholesome, Hype, Dead, etc.)
3. A short 2-3 sentence summary of the chat mood
4. An emoji that represents the vibe

Chat log:
{chat_log}

Format your response exactly like this:
Score: [number]/100
Vibe: [label]
Emoji: [emoji]
Summary: [summary]"""

        try:
            response = model.generate_content(prompt)
            result = response.text

            embed = discord.Embed(
                title="✨ Vibe Check",
                description=result,
                color=discord.Color.purple()
            )
            embed.set_footer(text=f"Last 20 messages analyzed • #{interaction.channel.name}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")


async def setup(bot):
    await bot.add_cog(AI(bot))