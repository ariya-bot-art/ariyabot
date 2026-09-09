import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import sys
import asyncio

# Ensure UTF-8 output encoding for Windows terminal console
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

intents = discord.Intents.all()

class AriyaBot(commands.Bot):
    async def setup_hook(self):
        print("⏳ Loading cogs...", flush=True)
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ Loaded {filename}", flush=True)
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}", flush=True)

        print("⏳ Syncing slash commands globally...", flush=True)
        synced = await self.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands globally!", flush=True)

# Support both ! and . prefixes for commands like .v limit, .v trust, .v lock
bot = AriyaBot(command_prefix=commands.when_mentioned_or("!", "."), intents=intents)

@bot.event
async def on_ready():
    print(f"🚀 Ariya ({bot.user}) is online and ready!", flush=True)

@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx):
    synced = await bot.tree.sync()
    await ctx.send(f"✅ Synced {len(synced)} slash commands globally!")

async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ ERROR: DISCORD_TOKEN is missing from environment variables!", flush=True)
        return
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())