import discord
from discord.ext import commands
import random
import string
import asyncio
from datetime import datetime, timedelta
import config
from database import Database
import traceback

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents)
db = Database()

@bot.event
async def on_ready():
    print(f'✅ Bot is online! Logged in as {bot.user}')
    print(f'✅ Bot is in {len(bot.guilds)} guilds')
    
    await db.init()
    print("✅ Database initialized!")
    
    await bot.change_presence(activity=discord.Game(name=".help for commands"))
    print("✅ Bot is ready!")

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="🤖 Protection Bot Commands", color=discord.Color.blue())
    embed.add_field(name="📋 Panel", value="`.setpanel <loader>`\n`.setbuyerrole <role>`", inline=True)
    embed.add_field(name="🔑 Keys", value="`.genkey <24h/7d>`\n`.freekey #channel`\n`.listkeys`", inline=True)
    embed.add_field(name="👤 Users", value="`.blacklist <user>`\n`.whitelist <user>`\n`.forceresethwid <user>`", inline=True)
    embed.add_field(name="🛡️ Mod", value="`.ban <user> [reason]`\n`.timeout <user> <min>`\n`.warn <user> <reason>`", inline=True)
    embed.add_field(name="📢 Other", value="`.update #channel <msg>`\n`.ping`", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 {round(bot.latency * 1000)}ms")

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🔑 Redeem Key", style=discord.ButtonStyle.primary)
    async def redeem_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RedeemModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🔄 Reset HWID", style=discord.ButtonStyle.secondary)
    async def reset_hwid_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ HWID reset!", ephemeral=True)
    
    @discord.ui.button(label="📜 Get Script", style=discord.ButtonStyle.success)
    async def script_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Script: `loader.lua`", ephemeral=True)
    
    @discord.ui.button(label="👑 Get Role", style=discord.ButtonStyle.danger)
    async def role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_data = db.fetchrow("SELECT role_id FROM buyer_roles WHERE guild_id = $1", interaction.guild_id)
        if role_data:
            role = interaction.guild.get_role(role_data['role_id'])
            if role:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ Got {role.name} role!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Role not found!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No role set! Use `.setbuyerrole`", ephemeral=True)

class RedeemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Redeem Key")
        self.key_input = discord.ui.TextInput(label="Enter your key:", placeholder="XXXX-XXXX-XXXX-XXXX", required=True)
        self.add_item(self.key_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.upper().strip()
        
        blacklisted = db.fetchrow("SELECT * FROM blacklist WHERE user_id = $1", interaction.user.id)
        if blacklisted:
            await interaction.response.send_message("❌ You are blacklisted!", ephemeral=True)
            return
        
        whitelisted = db.fetchrow("SELECT * FROM whitelist WHERE user_id = $1", interaction.user.id)
        if whitelisted:
            await interaction.response.send_message("✅ Whitelisted - lifetime access!", ephemeral=True)
            return
        
        key_data = db.fetchrow("SELECT * FROM keys WHERE key = $1 AND used = 0", key)
        if key_data:
            db.execute("UPDATE keys SET used = 1, used_by = $1 WHERE key = $2", interaction.user.id, key)
            await interaction.response.send_message("✅ Key redeemed! Access granted.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid or used key!", ephemeral=True)

@bot.command(name="setpanel")
async def setpanel(ctx, *, loader: str):
    embed = discord.Embed(title=f"🔒 {loader}", description="Use buttons below:", color=discord.Color.blue())
    await ctx.send(embed=embed, view=PanelView())
    await ctx.send("✅ Panel created!", delete_after=3)

@bot.command(name="setbuyerrole")
async def setbuyerrole(ctx, role: discord.Role):
    db.execute("INSERT INTO buyer_roles (guild_id, role_id) VALUES ($1, $2) ON CONFLICT(guild_id) DO UPDATE SET role_id = $2", ctx.guild.id, role.id)
    await ctx.send(f"✅ Buyer role set to {role.mention}")

@bot.command(name="genkey")
async def genkey(ctx, duration: str):
    if duration.endswith('h'):
        hours = int(duration[:-1])
        time_text = f"{hours} hours"
    elif duration.endswith('d'):
        days = int(duration[:-1])
        hours = days * 24
        time_text = f"{days} days"
    else:
        await ctx.send("❌ Use 24h or 7d format!")
        return
    
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit) VALUES ($1, $2, $3, $4)", key, ctx.guild.id, ctx.channel.id, hours)
    await ctx.send(f"✅ Key: `{key}`\n⏰ Duration: {time_text}")

@bot.command(name="forceresethwid")
async def forceresethwid(ctx, user: discord.User):
    await ctx.send(f"✅ HWID reset for {user.mention}")

@bot.command(name="blacklist")
async def blacklist(ctx, user: discord.User):
    db.execute("INSERT INTO blacklist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await ctx.send(f"✅ {user.mention} blacklisted")

@bot.command(name="whitelist")
async def whitelist(ctx, user: discord.User):
    db.execute("INSERT INTO whitelist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await ctx.send(f"✅ {user.mention} whitelisted (lifetime)")

@bot.command(name="freekey")
async def freekey(ctx, channel: discord.TextChannel):
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit, used) VALUES ($1, $2, $3, $4, $5)", key, ctx.guild.id, channel.id, 24, 0)
    
    embed = discord.Embed(title="🎉 FREE KEY DROP!", description=f"**Key:** `{key}`\n**Duration:** 24 hours", color=discord.Color.gold())
    
    class CopyButton(discord.ui.View):
        def __init__(self, k):
            super().__init__(timeout=60)
            self.k = k
        @discord.ui.button(label="📋 Copy", style=discord.ButtonStyle.primary)
        async def copy(self, i, b):
            await i.response.send_message(f"✅ `{self.k}`", ephemeral=True)
    
    await channel.send("@everyone 🎁 FREE KEY!", embed=embed, view=CopyButton(key))
    await ctx.send(f"✅ Free key dropped in {channel.mention}")

@bot.command(name="update")
async def update(ctx, channel: discord.TextChannel, *, message: str):
    embed = discord.Embed(title="📢 Updates", description=message, color=discord.Color.blue(), timestamp=datetime.now())
    embed.set_footer(text=f"Posted by {ctx.author.name}")
    await channel.send(embed=embed)
    await ctx.send(f"✅ Update posted in {channel.mention}")

@bot.command(name="ban")
async def ban(ctx, user: discord.User, *, reason: str = "No reason"):
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("❌ No permission!")
        return
    member = ctx.guild.get_member(user.id)
    if member:
        await member.ban(reason=reason)
        await ctx.send(f"✅ Banned {user.mention}")
    else:
        await ctx.send("❌ User not found")

@bot.command(name="timeout")
async def timeout(ctx, user: discord.Member, minutes: int, *, reason: str = "No reason"):
    if not ctx.author.guild_permissions.moderate_members:
        await ctx.send("❌ No permission!")
        return
    await user.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"✅ Timed out {user.mention} for {minutes}min")

@bot.command(name="warn")
async def warn(ctx, user: discord.User, *, reason: str):
    embed = discord.Embed(title="⚠️ Warning", description=f"In {ctx.guild.name}\nReason: {reason}", color=discord.Color.orange())
    try:
        await user.send(embed=embed)
        await ctx.send(f"✅ Warned {user.mention} (DM sent)")
    except:
        await ctx.send(f"✅ Warned {user.mention} (DM failed)")

@bot.command(name="listkeys")
async def listkeys(ctx):
    keys = db.fetch("SELECT key, time_limit FROM keys WHERE used = 0 LIMIT 10")
    if keys:
        msg = "\n".join([f"`{k['key']}` - {k['time_limit']}h" for k in keys])
        await ctx.send(f"📋 **Unused Keys:**\n{msg}")
    else:
        await ctx.send("No unused keys.")

async def keep_alive():
    while True:
        await asyncio.sleep(300)
        print("Alive...")

if __name__ == "__main__":
    print("Starting...")
    asyncio.create_task(keep_alive())
    bot.run(config.TOKEN)
