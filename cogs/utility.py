import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
from dotenv import load_dotenv
import json
import os
from datetime import datetime

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

ECONOMY_FILE = "economy.json"
NEWSPAPER_FILE = "newspaper.json"

def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== MEETING SCHEDULER ====================
    @app_commands.command(name="schedule", description="Find the best meeting time for everyone!")
    @app_commands.describe(
        timezones="List timezones separated by commas (e.g. GMT+8, EST, PST)",
        duration="How long is the meeting? (e.g. 1 hour)"
    )
    async def schedule(self, interaction: discord.Interaction, timezones: str, duration: str):
        await interaction.response.defer()

        prompt = f"""Help find the best meeting time for people in these timezones: {timezones}
Meeting duration: {duration}
Current UTC time: {datetime.utcnow().strftime("%H:%M")}

Suggest 3 meeting times that work well for everyone.
Format each suggestion like this:
Option [number]:
- UTC: [time]
- [timezone1]: [local time]
- [timezone2]: [local time]
[etc for each timezone]
Why it works: [brief explanation]"""

        response = model.generate_content(prompt)

        embed = discord.Embed(
            title="📅 Meeting Scheduler",
            description=response.text,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Timezones: {timezones} • Duration: {duration}")
        await interaction.followup.send(embed=embed)

    # ==================== SERVER NEWSPAPER ====================
    @app_commands.command(name="newspaper", description="Generate a weekly server newspaper!")
    async def newspaper(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Collect messages from all accessible channels
        all_messages = []
        for channel in interaction.guild.text_channels:
            try:
                async for msg in channel.history(limit=30):
                    if not msg.author.bot and msg.content:
                        all_messages.append(f"#{channel.name} - {msg.author.display_name}: {msg.content}")
            except:
                continue

        if not all_messages:
            await interaction.followup.send("❌ No messages found to generate newspaper!")
            return

        # Limit to 100 messages
        all_messages = all_messages[:100]
        chat_log = "\n".join(all_messages)

        prompt = f"""You are a fun Discord server newspaper editor. Based on these server messages, create a fun weekly newspaper.

Messages:
{chat_log}

Create a newspaper with these sections:
📰 HEADLINE NEWS: [biggest topic being discussed]
🌟 MEMBER SPOTLIGHT: [most active/interesting member]
💬 QUOTE OF THE WEEK: [interesting quote from the messages]
🔥 HOT TOPICS: [top 3 things people talked about]
😂 FUNNY MOMENT: [funniest thing that happened]
📊 SERVER MOOD: [overall vibe of the server this week]

Keep it fun, positive and entertaining!"""

        response = model.generate_content(prompt)

        embed = discord.Embed(
            title=f"📰 {interaction.guild.name} Weekly Newspaper",
            description=response.text,
            color=discord.Color.og_blurple()
        )
        embed.set_footer(text=f"Generated on {datetime.now().strftime('%B %d, %Y')}")
        await interaction.followup.send(embed=embed)

    # ==================== SUMMARIZE ====================
    @app_commands.command(name="summarize", description="Summarize the last messages in this channel!")
    @app_commands.describe(amount="How many messages to summarize? (max 50)")
    async def summarize(self, interaction: discord.Interaction, amount: int = 20):
        await interaction.response.defer()

        if amount > 50:
            amount = 50

        messages = []
        async for msg in interaction.channel.history(limit=amount):
            if not msg.author.bot and msg.content:
                messages.append(f"{msg.author.display_name}: {msg.content}")

        if not messages:
            await interaction.followup.send("❌ No messages found!")
            return

        chat_log = "\n".join(reversed(messages))

        prompt = f"""Summarize this Discord conversation in a clear and concise way.
Include:
- Main topics discussed
- Key points made
- Any decisions or conclusions reached

Conversation:
{chat_log}"""

        response = model.generate_content(prompt)

        embed = discord.Embed(
            title=f"📝 Chat Summary — Last {amount} Messages",
            description=response.text,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"#{interaction.channel.name}")
        await interaction.followup.send(embed=embed)

    # ==================== POLL ====================
    @app_commands.command(name="poll", description="Create a poll!")
    @app_commands.describe(
        question="Poll question",
        options="Options separated by commas (e.g. Yes, No, Maybe)"
    )
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        option_list = [o.strip() for o in options.split(",")][:5]

        if len(option_list) < 2:
            await interaction.response.send_message("❌ Please provide at least 2 options!")
            return

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

        description = ""
        for i, option in enumerate(option_list):
            description += f"{emojis[i]} {option}\n"

        embed = discord.Embed(
            title=f"📊 {question}",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Poll by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        for i in range(len(option_list)):
            await message.add_reaction(emojis[i])

    # ==================== GIVE COINS ====================
    @app_commands.command(name="give", description="Give coins to another member!")
    @app_commands.describe(user="Who to give coins to", amount="How many coins to give")
    async def give(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        economy_data = load_data(ECONOMY_FILE)
        sender_id = str(interaction.user.id)
        receiver_id = str(user.id)

        if sender_id not in economy_data or economy_data[sender_id]["coins"] < amount:
            await interaction.response.send_message("❌ You don't have enough coins!")
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be greater than 0!")
            return

        economy_data[sender_id]["coins"] -= amount

        if receiver_id not in economy_data:
            economy_data[receiver_id] = {"coins": 0, "total_earned": 0}

        economy_data[receiver_id]["coins"] += amount
        save_data(ECONOMY_FILE, economy_data)

        embed = discord.Embed(
            title="🪙 Coins Transferred!",
            color=discord.Color.green()
        )
        embed.add_field(name="From", value=interaction.user.mention, inline=True)
        embed.add_field(name="To", value=user.mention, inline=True)
        embed.add_field(name="Amount", value=f"🪙 {amount} coins", inline=False)
        await interaction.response.send_message(embed=embed)

    # ==================== USERINFO ====================
    @app_commands.command(name="userinfo", description="Get info about a member!")
    @app_commands.describe(user="Which member?")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        economy_data = load_data(ECONOMY_FILE)
        user_id = str(user.id)

        embed = discord.Embed(
            title=f"👤 {user.display_name}",
            color=user.color
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Username", value=str(user), inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Roles", value=", ".join([r.mention for r in user.roles[1:]]) or "None", inline=False)
        embed.add_field(name="🪙 Coins", value=economy_data.get(user_id, {}).get("coins", 0), inline=True)
        await interaction.response.send_message(embed=embed)

    # ==================== SERVERINFO ====================
    @app_commands.command(name="serverinfo", description="Get info about this server!")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild

        embed = discord.Embed(
            title=f"🏠 {guild.name}",
            color=discord.Color.blue()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Boost Level", value=f"Level {guild.premium_tier}", inline=True)
    # ==================== PING & BOT STATUS ====================
    @app_commands.command(name="ping", description="Check Ariya's latency and system health 📡")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** `{latency}ms`\n**Status:** `🟢 Operational 24/7`",
            color=discord.Color.green() if latency < 150 else discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botinfo", description="View Ariya's official statistics & system status 🤖")
    async def botinfo(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        total_members = sum(g.member_count for g in self.bot.guilds if g.member_count)
        
        embed = discord.Embed(
            title="🤖 Ariya — Bot Overview & Stats",
            description="Your all-in-one AI companion powered by Google Gemini!",
            color=discord.Color.purple()
        )
        if self.bot.user and self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        embed.add_field(name="🌐 Servers", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="👥 Total Users", value=f"`{total_members}`", inline=True)
        embed.add_field(name="📡 Latency", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="🧠 AI Model", value="`Gemini 2.5 Flash`", inline=True)
        embed.add_field(name="⚡ Hosting", value="`Railway 24/7 Cloud`", inline=True)
        embed.add_field(name="🐍 Python", value="`v3.13`", inline=True)
        
        embed.set_footer(text="Ariya Discord Bot • Official Build")
        await interaction.response.send_message(embed=embed)

    # ==================== INVITE ====================
    @app_commands.command(name="invite", description="Get Ariya's official invite link! 🔗")
    async def invite(self, interaction: discord.Interaction):
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands"
        
        embed = discord.Embed(
            title="✨ Invite Ariya to Your Server!",
            description="Bring Gemini AI, Music, Daily Challenges, Economy & Moderation to your community today!",
            color=discord.Color.gold()
        )
        if self.bot.user and self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Add Ariya to Server 🤖", url=invite_url, style=discord.ButtonStyle.link))
        
    # ==================== AUTOMATIC SERVER SETUP ====================
    @app_commands.command(name="setup_server", description="Automatically build a professional Bot Support server layout! 🏗️")
    @app_commands.default_permissions(administrator=True)
    async def setup_server(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        # 1. Information Category
        info_cat = await guild.create_category("📌 INFORMATION & LINKS")
        welcome_ch = await info_cat.create_text_channel("welcome")
        announce_ch = await info_cat.create_text_channel("announcements")
        privacy_ch = await info_cat.create_text_channel("privacy-policy")
        faq_ch = await info_cat.create_text_channel("faq-and-commands")
        status_ch = await info_cat.create_text_channel("bot-status")

        # 2. Community Category
        comm_cat = await guild.create_category("💬 COMMUNITY & LOUNGE")
        await comm_cat.create_text_channel("general-chat")
        await comm_cat.create_text_channel("bot-commands")
        await comm_cat.create_text_channel("suggestions")

        # 3. Support Category
        supp_cat = await guild.create_category("🛠️ SUPPORT & TICKETS")
        await supp_cat.create_text_channel("support-tickets")
        await supp_cat.create_text_channel("bug-reports")

        # 4. VIP Category
        vip_cat = await guild.create_category("👑 VIP & VOTERS")
        await vip_cat.create_text_channel("voter-perks")

        # Save welcome channel to config
        config = load_data("config.json")
        config["welcome_channel"] = welcome_ch.id
        save_data("config.json", config)

        # Post Welcome Embed
        welcome_embed = discord.Embed(
            title="👋 Welcome to the Official Ariya Support Server!",
            description="Ariya is your all-in-one **Gemini AI companion** for Discord with Music, Economy, Daily Challenges, Fun & Moderation!\n\n"
                        f"📌 **Quick Links**\n"
                        f"📜 **Privacy Policy:** <#{privacy_ch.id}>\n"
                        f"❓ **Commands List:** <#{faq_ch.id}>\n"
                        f"📡 **Bot Status:** <#{status_ch.id}>\n\n"
                        "Enjoy your stay and happy chatting! 🚀",
            color=discord.Color.purple()
        )
        if self.bot.user and self.bot.user.display_avatar:
            welcome_embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await welcome_ch.send(embed=welcome_embed)

        # Post Privacy Policy Embed
        privacy_embed = discord.Embed(
            title="📜 Privacy Policy for Ariya Discord Bot",
            description="*Effective Date: September 9, 2026*\n\n"
                        "### 1. Data We Collect & Store\n"
                        "• **User & Guild IDs:** To save user balances & preferences.\n"
                        "• **Economy Data:** Coin balances (`/balance`, `/give`).\n"
                        "• **Moderation History:** Warning records (`/warn`).\n"
                        "• **Challenge Data:** Leaderboard ranks (`/challenge`).\n"
                        "• **AI Chat Context:** Temporary prompt memory (`/chat`).\n\n"
                        "### 2. Privacy & Usage\n"
                        "Data is stored securely, used strictly for bot features, and **never sold** or shared.",
            color=discord.Color.blue()
        )
        await privacy_ch.send(embed=privacy_embed)

        # Post FAQ Embed
        faq_embed = discord.Embed(
            title="❓ Ariya Commands & FAQ Guide",
            description="Use `/help` anywhere to view all available commands!\n\n"
                        "🤖 **AI:** `/chat`, `/clearchat`, `/vibe`\n"
                        "🎵 **Music:** `/play`, `/pause`, `/resume`, `/skip`, `/stop`, `/queue`, `/leave`\n"
                        "😂 **Fun:** `/ship`, `/drama`, `/roast`, `/trivia`, `/8ball`, `/meme`, `/confess`\n"
                        "🎯 **Daily:** `/challenge`, `/complete`, `/leaderboard`, `/balance`\n"
                        "🛠️ **Utility:** `/schedule`, `/newspaper`, `/summarize`, `/poll`, `/give`, `/userinfo`, `/serverinfo`, `/botinfo`, `/ping`, `/invite`, `/setup_server`\n"
                        "🔨 **Moderation:** `/kick`, `/ban`, `/mute`, `/warn`, `/purge`, `/lock`, `/slowmode`, `/setwelcome`",
            color=discord.Color.gold()
        )
        await faq_ch.send(embed=faq_embed)

        # Post Status Embed
        status_embed = discord.Embed(
            title="📡 Ariya Operational Status",
            description=f"**Status:** `🟢 Operational 24/7`\n"
                        f"**Latency:** `{round(self.bot.latency * 1000)}ms`\n"
                        f"**Hosting:** `Railway Cloud`\n"
                        f"**AI Engine:** `Google Gemini 2.5 Flash`",
            color=discord.Color.green()
        )
        await status_ch.send(embed=status_embed)

        await interaction.followup.send("🎉 **Server Setup Complete!** Ariya created all categories, channels, and posted official info embeds!")


async def setup(bot):
    await bot.add_cog(Utility(bot))