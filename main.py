import discord
from discord.ext import commands
import random
import string
import asyncio
import secrets
from datetime import datetime, timedelta
import config
from database import Database
import json

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents)
db = Database()

bot.remove_command('help')

# Your actual script content (this is what gets loaded)
SCRIPT_CONTENT = """
-- Your Actual Lua Script Here
-- This is protected and only visible to paid users

print("Script loaded successfully!")
-- Add your real script logic here

-- Example protection check
local whitelist = {{
    -- User IDs will be auto-added when they redeem key
}}

local function checkAccess()
    -- Your anti-tamper code here
    return true
end

if checkAccess() then
    -- Your main script code
    print("Access granted!")
    -- YOUR ACTUAL SCRIPT GOES HERE
end
"""

@bot.event
async def on_ready():
    print(f'✅ Bot online! {bot.user}')
    await db.init()
    await bot.change_presence(activity=discord.Game(name=".help"))
    print('✅ Ready!')

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="🔒 Protection Bot", color=discord.Color.blue())
    embed.add_field(name="📋 Panel", value="`.setpanel <loader>`\n`.setbuyerrole <role>`", inline=True)
    embed.add_field(name="💰 Keys", value="`.genkey <24h/7d/30d>`\n`.freekey #channel`\n`.listkeys`", inline=True)
    embed.add_field(name="👤 Users", value="`.addwhitelist <user>`\n`.removewhitelist <user>`\n`.checkaccess <user>`", inline=True)
    embed.add_field(name="🛡️ Admin", value="`.ban/timeout/warn`\n`.update`\n`.setprice <amount>`", inline=True)
    await ctx.send(embed=embed)

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="💳 Buy Access", style=discord.ButtonStyle.success, emoji="💰")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💳 Purchase Access",
            description="To get access, purchase a key from our store!\n\nAfter purchase, use the **Redeem Key** button.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🔑 Redeem Key", style=discord.ButtonStyle.primary, emoji="🔑")
    async def redeem_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RedeemModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📜 Get Script", style=discord.ButtonStyle.secondary, emoji="📜")
    async def script_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has access
        has_access = db.fetchrow("SELECT * FROM whitelist WHERE user_id = $1", interaction.user.id)
        key_used = db.fetchrow("SELECT * FROM keys WHERE used_by = $1 AND used = 1", interaction.user.id)
        
        if has_access or key_used:
            # Generate unique loadstring for this user
            user_hash = secrets.token_hex(8)
            loadstring_url = f"https://your-api.com/script?user={interaction.user.id}&hash={user_hash}"
            
            embed = discord.Embed(
                title="📜 Your Script Loader",
                description=f"```lua\nloadstring(game:HttpGet(\"{loadstring_url}\"))()\n```",
                color=discord.Color.green()
            )
            embed.add_field(name="⚠️ Note", value="This loader is unique to you. Don't share it!", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have access to this script!\n\nPurchase a key and redeem it first.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="👑 Get Role", style=discord.ButtonStyle.danger, emoji="👑")
    async def role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_access = db.fetchrow("SELECT * FROM whitelist WHERE user_id = $1", interaction.user.id)
        key_used = db.fetchrow("SELECT * FROM keys WHERE used_by = $1 AND used = 1", interaction.user.id)
        
        if has_access or key_used:
            role_data = db.fetchrow("SELECT role_id FROM buyer_roles WHERE guild_id = $1", interaction.guild_id)
            if role_data:
                role = interaction.guild.get_role(role_data['role_id'])
                if role:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message(f"✅ You got the {role.name} role!", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Role not found!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ No buyer role set! Use `.setbuyerrole`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You need to purchase access first!", ephemeral=True)

class RedeemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Redeem Key")
        self.key_input = discord.ui.TextInput(label="Enter your key:", placeholder="XXXX-XXXX-XXXX-XXXX", required=True)
        self.add_item(self.key_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.upper().strip()
        
        # Check if already whitelisted
        whitelisted = db.fetchrow("SELECT * FROM whitelist WHERE user_id = $1", interaction.user.id)
        if whitelisted:
            await interaction.response.send_message("✅ You already have lifetime access!", ephemeral=True)
            return
        
        # Check key
        key_data = db.fetchrow("SELECT * FROM keys WHERE key = $1 AND used = 0", key)
        if key_data:
            # Mark key as used
            db.execute("UPDATE keys SET used = 1, used_by = $1 WHERE key = $2", interaction.user.id, key)
            
            # Auto-whitelist the user
            db.execute("INSERT INTO whitelist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", interaction.user.id)
            
            # Generate their personal loadstring
            user_hash = secrets.token_hex(8)
            
            embed = discord.Embed(
                title="✅ Access Granted!",
                description=f"You now have access to the script!\n\n**Your Loader:**",
                color=discord.Color.green()
            )
            embed.add_field(name="📜 Loadstring", value=f"```lua\nloadstring(game:HttpGet(\"https://your-api.com/script?user={interaction.user.id}\"))()\n```", inline=False)
            embed.add_field(name="💡 Tip", value="Click 'Get Script' on the panel anytime to get your loader again.", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log to channel
            log_channel = discord.utils.get(interaction.guild.text_channels, name="key-logs")
            if log_channel:
                await log_channel.send(f"✅ {interaction.user} redeemed key: `{key}`")
        else:
            await interaction.response.send_message("❌ Invalid or already used key!", ephemeral=True)

# ============= ADMIN COMMANDS =============

@bot.command(name="setpanel")
async def setpanel(ctx, *, loader: str):
    """Create a protection panel"""
    embed = discord.Embed(
        title=f"🔒 {loader}",
        description="**Get access to our protected script!**\n\n💳 **Buy Access** - Purchase a key\n🔑 **Redeem Key** - Enter your purchased key\n📜 **Get Script** - Get your loadstring\n👑 **Get Role** - Get your buyer role",
        color=discord.Color.blue()
    )
    embed.set_footer(text="DM an admin to purchase a key")
    await ctx.send(embed=embed, view=PanelView())
    await ctx.send("✅ Panel created!")

@bot.command(name="setbuyerrole")
async def setbuyerrole(ctx, role: discord.Role):
    """Set the role for buyers"""
    db.execute("INSERT INTO buyer_roles (guild_id, role_id) VALUES ($1, $2) ON CONFLICT(guild_id) DO UPDATE SET role_id = $2", ctx.guild.id, role.id)
    await ctx.send(f"✅ Buyer role set to {role.mention}")

@bot.command(name="genkey")
async def genkey(ctx, duration: str):
    """Generate a key - Usage: .genkey 24h/7d/30d"""
    if duration.endswith('h'):
        hours = int(duration[:-1])
        time_text = f"{hours} hours"
    elif duration.endswith('d'):
        days = int(duration[:-1])
        hours = days * 24
        time_text = f"{days} days"
    else:
        await ctx.send("❌ Use 24h, 7d, or 30d format!")
        return
    
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit) VALUES ($1, $2, $3, $4)", 
               key, ctx.guild.id, ctx.channel.id, hours)
    
    embed = discord.Embed(title="🎫 Key Generated", color=discord.Color.green())
    embed.add_field(name="Key", value=f"`{key}`", inline=False)
    embed.add_field(name="Duration", value=time_text, inline=True)
    embed.add_field(name="Status", value="Unused", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="addwhitelist")
async def addwhitelist(ctx, user: discord.User):
    """Manually whitelist a user (lifetime access)"""
    db.execute("INSERT INTO whitelist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await ctx.send(f"✅ {user.mention} has been whitelisted (lifetime access)")

@bot.command(name="removewhitelist")
async def removewhitelist(ctx, user: discord.User):
    """Remove a user from whitelist"""
    db.execute("DELETE FROM whitelist WHERE user_id = $1", user.id)
    await ctx.send(f"❌ {user.mention} removed from whitelist")

@bot.command(name="checkaccess")
async def checkaccess(ctx, user: discord.User):
    """Check if a user has access"""
    whitelisted = db.fetchrow("SELECT * FROM whitelist WHERE user_id = $1", user.id)
    key_used = db.fetchrow("SELECT * FROM keys WHERE used_by = $1 AND used = 1", user.id)
    
    if whitelisted:
        await ctx.send(f"✅ {user.mention} has **LIFETIME** access")
    elif key_used:
        await ctx.send(f"✅ {user.mention} has access (key redeemed)")
    else:
        await ctx.send(f"❌ {user.mention} does NOT have access")

@bot.command(name="freekey")
async def freekey(ctx, channel: discord.TextChannel):
    """Drop a free key"""
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit, used) VALUES ($1, $2, $3, $4, $5)", 
               key, ctx.guild.id, channel.id, 24, 0)
    
    embed = discord.Embed(title="🎉 FREE KEY DROP!", description=f"**Key:** `{key}`\n**Duration:** 24 hours", color=discord.Color.gold())
    
    class CopyButton(discord.ui.View):
        def __init__(self, k):
            super().__init__(timeout=60)
            self.k = k
        @discord.ui.button(label="📋 Copy Key", style=discord.ButtonStyle.primary)
        async def copy(self, i, b):
            await i.response.send_message(f"✅ Key: `{self.k}`", ephemeral=True)
    
    await channel.send("@everyone 🎁 **FREE KEY DROP!**", embed=embed, view=CopyButton(key))
    await ctx.send(f"✅ Free key dropped in {channel.mention}")

@bot.command(name="listkeys")
async def listkeys(ctx):
    """List all unused keys"""
    keys = db.fetch("SELECT key, time_limit FROM keys WHERE used = 0 LIMIT 10")
    if keys:
        msg = "\n".join([f"`{k['key']}` - {k['time_limit']} hours" for k in keys])
        await ctx.send(f"📋 **Unused Keys:**\n{msg}")
    else:
        await ctx.send("No unused keys.")

@bot.command(name="update")
async def update(ctx, channel: discord.TextChannel, *, message: str):
    """Post an update"""
    embed = discord.Embed(title="📢 Update", description=message, color=discord.Color.blue(), timestamp=datetime.now())
    embed.set_footer(text=f"Posted by {ctx.author.name}")
    await channel.send(embed=embed)
    await ctx.send(f"✅ Update posted")

# Moderation commands
@bot.command(name="ban")
async def ban(ctx, user: discord.User, *, reason: str = "No reason"):
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("❌ No permission!")
        return
    member = ctx.guild.get_member(user.id)
    if member:
        await member.ban(reason=reason)
        await ctx.send(f"✅ Banned {user.mention}")

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
        await ctx.send(f"✅ Warned {user.mention}")
    except:
        await ctx.send(f"✅ Warned {user.mention} (DM failed)")

# Keep alive
async def keep_alive():
    while True:
        await asyncio.sleep(300)
        print("Bot alive...")

if __name__ == "__main__":
    print("Starting Protection Bot...")
    loop = asyncio.get_event_loop()
    loop.create_task(keep_alive())
    bot.run(config.TOKEN)
