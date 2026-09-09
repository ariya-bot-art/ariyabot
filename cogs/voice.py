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

    def get_user_room(self, member: discord.Member):
        if not member.voice or not member.voice.channel:
            return None, False

        channel = member.voice.channel
        g_id = str(member.guild.id)

        if g_id in self.temp_channels and channel.id in self.temp_channels[g_id]:
            owner_id = self.temp_channels[g_id][channel.id]
            is_owner = (member.id == owner_id or member.guild_permissions.administrator)
            return channel, is_owner
        return None, False

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
                        f"**Prefix Controls:** Use `.v limit`, `.v trust`, `.v reject`, `.v lock`, `.v unlock`, `.v name`, `.v kick`, `.v claim`!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

    # ==================== .v PREFIX COMMAND GROUP ====================
    @commands.group(name="v", invoke_without_command=True)
    async def v_group(self, ctx):
        embed = discord.Embed(
            title="🔊 Voice Room Commands (`.v`)",
            description="Control your temporary voice room:\n\n"
                        "`.v lock` — Lock your voice room\n"
                        "`.v unlock` — Unlock your voice room\n"
                        "`.v limit <number>` — Set user limit (0-99)\n"
                        "`.v trust <@user>` — Trust/allow user into locked room\n"
                        "`.v reject <@user>` — Ban user from your voice room\n"
                        "`.v name <new_name>` — Rename your voice room\n"
                        "`.v kick <@user>` — Disconnect user from room\n"
                        "`.v claim` — Claim ownership if owner left",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    @v_group.command(name="lock")
    async def v_lock(self, ctx):
        channel, is_owner = self.get_user_room(ctx.author)
        if not channel:
            await ctx.send("❌ You are not in a temporary voice room!")
            return
        if not is_owner:
            await ctx.send("❌ Only the room owner can lock this channel!")
            return

        await channel.set_permissions(ctx.guild.default_role, connect=False)
        await ctx.send("🔒 Voice room **locked**!")

    @v_group.command(name="unlock")
    async def v_unlock(self, ctx):
        channel, is_owner = self.get_user_room(ctx.author)
        if not channel:
            await ctx.send("❌ You are not in a temporary voice room!")
            return
        if not is_owner:
            await ctx.send("❌ Only the room owner can unlock this channel!")
            return

        await channel.set_permissions(ctx.guild.default_role, connect=True)
        await ctx.send("🔓 Voice room **unlocked**!")

    @v_group.command(name="limit")
    async def v_limit(self, ctx, limit: int):
        channel, is_owner = self.get_user_room(ctx.author)
        if not channel:
            await ctx.send("❌ You are not in a temporary voice room!")
            return
        if not is_owner:
            await ctx.send("❌ Only the room owner can set the limit!")
            return

        if limit < 0 or limit > 99:
            await ctx.send("❌ Limit must be between 0 and 99!")
            return

        await channel.edit(user_limit=limit)
        limit_text = "unlimited" if limit == 0 else f"{limit} members"
        await ctx.send(f"👥 Set room limit to **{limit_text}**!")

    @v_group.command(name="trust")
    async def v_trust(self, ctx, member: discord.Member):
        channel, is_owner = self.get_user_room(ctx.author)
        if not channel:
            await ctx.send("❌ You are not in a temporary voice room!")
            return
        if not is_owner:
            await ctx.send("❌ Only the room owner can trust users!")
            return

        await channel.set_permissions(member, connect=True)
        await ctx.send(f"✅ Trusted {member.mention}! They can join even if room is locked.")

    @v_group.command(name="reject")
    async def v_reject(self, ctx, member: discord.Member):
        channel, is_owner = self.get_user_room(ctx.author)
        if not channel:
            await ctx.send("❌ You are not in a temporary voice room!")
            return
        if not is_owner:
            await ctx.send("❌ Only the room owner can reject users!")
            return

        await channel.set_permissions(member, connect=False)
        if member.voice and member.voice.channel == channel:
            await member.move_to(None)
        await ctx.send(f"🚫 Rejected {member.mention} from your voice room!")

    @v_group.command(name="name")
    async def v_name(self, ctx, *, new_name: str):
        channel, is_owner = self.get_user_room(ctx.author)
        if not channel:
            await ctx.send("❌ You are not in a temporary voice room!")
            return
        if not is_owner:
            await ctx.send("❌ Only the room owner can rename the channel!")
            return

        await channel.edit(name=f"🔊 {new_name}")
        await ctx.send(f"✅ Renamed voice room to **🔊 {new_name}**!")

    @v_group.command(name="kick")
    async def v_kick(self, ctx, member: discord.Member):
        channel, is_owner = self.get_user_room(ctx.author)
        if not channel:
            await ctx.send("❌ You are not in a temporary voice room!")
            return
        if not is_owner:
            await ctx.send("❌ Only the room owner can kick users!")
            return

        if member.voice and member.voice.channel == channel:
            await member.move_to(None)
            await ctx.send(f"👢 Kicked {member.mention} from your voice room!")
        else:
            await ctx.send("❌ User is not in your voice room!")

    @v_group.command(name="claim")
    async def v_claim(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ You are not in a voice channel!")
            return

        channel = ctx.author.voice.channel
        g_id = str(ctx.guild.id)

        if g_id in self.temp_channels and channel.id in self.temp_channels[g_id]:
            owner_id = self.temp_channels[g_id][channel.id]
            owner = ctx.guild.get_member(owner_id)

            if owner and owner in channel.members and owner.id != ctx.author.id:
                await ctx.send("❌ The room owner is still in this channel!")
                return

            self.temp_channels[g_id][channel.id] = ctx.author.id
            await ctx.send(f"👑 {ctx.author.mention} is now the owner of this voice room!")
        else:
            await ctx.send("❌ You are not in a temporary voice room!")


async def setup(bot):
    await bot.add_cog(Voice(bot))
