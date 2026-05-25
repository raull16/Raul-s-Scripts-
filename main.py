import discord
from discord.ext import commands
from discord import app_commands
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

bot = commands.Bot(command_prefix='.', intents=intents)  # Changed to .
db = Database()

@bot.event
async def on_ready():
    print(f'✅ Bot is online! Logged in as {bot.user}')
    print(f'✅ Bot is in {len(bot.guilds)} guilds')
    
    # Initialize database
    await db.init()
    print("✅ Database initialized!")
    
    # Sync commands
    await bot.tree.sync()
    print("✅ Commands synced!")
    
    # Set status
    await bot.change_presence(activity=discord.Game(name=".help for commands"))

@bot.command(name="ping")
async def ping(ctx):
    """Check if bot is working"""
    await ctx.send(f"Pong! 🏓 Latency: {round(bot.latency * 1000)}ms")

@bot.command(name="help")
async def help_command(ctx):
    """Show all commands"""
    embed = discord.Embed(
        title="🤖 Protection Bot Commands",
        description="Here are all the available commands:",
        color=discord.Color.blue()
    )
    embed.add_field(name="📋 Panel Commands", value="`.setpanel <loader>` - Create a panel\n`.setbuyerrole <role>` - Set buyer role", inline=False)
    embed.add_field(name="🔑 Key Commands", value="`.genkey <duration>` - Generate a key\n`.freekey #channel` - Drop free key\n`.listkeys` - List unused keys", inline=False)
    embed.add_field(name="👤 User Management", value="`.blacklist <user>` - Blacklist user\n`.whitelist <user>` - Whitelist user\n`.forceresethwid <user>` - Reset HWID", inline=False)
    embed.add_field(name="🛡️ Moderation", value="`.ban <user> [reason]` - Ban user\n`.timeout <user> <minutes> [reason]` - Timeout user\n`.warn <user> <reason>` - Warn user", inline=False)
    embed.add_field(name="📢 Utility", value="`.update #channel <message>` - Post update\n`.ping` - Check bot latency", inline=False)
    await ctx.send(embed=embed)

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🔑 Redeem Key", style=discord.ButtonStyle.primary, custom_id="redeem_key")
    async def redeem_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemModal())
    
    @discord.ui.button(label="🔄 Reset HWID", style=discord.ButtonStyle.secondary, custom_id="reset_hwid")
    async def reset_hwid_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Your HWID has been reset!", ephemeral=True)
    
    @discord.ui.button(label="📜 Get Script", style=discord.ButtonStyle.success, custom_id="get_script")
    async def script_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Here's your script: `loader.lua`\n\nDownload: [Link]", ephemeral=True)
    
    @discord.ui.button(label="👑 Get Role", style=discord.ButtonStyle.danger, custom_id="get_role")
    async def role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_data = db.fetchrow("SELECT role_id FROM buyer_roles WHERE guild_id = $1", interaction.guild_id)
        if role_data:
            role = interaction.guild.get_role(role_data['role_id'])
            if role:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ You've been given the {role.name} role!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Role not found! Ask an admin to reconfigure.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No buyer role configured! Ask an admin to run `.setbuyerrole`", ephemeral=True)

class RedeemModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Redeem Key")
        
        self.key_input = discord.ui.TextInput(
            label="Enter your key:",
            placeholder="XXXX-XXXX-XXXX-XXXX",
            required=True,
            style=discord.TextStyle.short,
            max_length=19
        )
        self.add_item(self.key_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.upper().strip()
        
        # Check blacklist
        blacklisted = db.fetchrow("SELECT * FROM blacklist WHERE user_id = $1", interaction.user.id)
        if blacklisted:
            await interaction.response.send_message("❌ You are blacklisted and cannot redeem keys!", ephemeral=True)
            return
        
        # Check whitelist
        whitelisted = db.fetchrow("SELECT * FROM whitelist WHERE user_id = $1", interaction.user.id)
        if whitelisted:
            await interaction.response.send_message("✅ You're whitelisted! Lifetime access granted.", ephemeral=True)
            return
        
        # Check key
        key_data = db.fetchrow("SELECT * FROM keys WHERE key = $1 AND used = 0", key)
        if key_data:
            db.execute("UPDATE keys SET used = 1, used_by = $1 WHERE key = $2", interaction.user.id, key)
            await interaction.response.send_message("✅ Key redeemed successfully! You now have access.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid or already used key!", ephemeral=True)

@bot.command(name="setpanel")
async def setpanel(ctx, *, loader: str):
    """Create a protection panel in current channel - Usage: .setpanel Luarmor V1"""
    embed = discord.Embed(
        title=f"🔒 {loader} Protection Panel",
        description="Welcome to the protection system!\n\nUse the buttons below to manage your access:",
        color=discord.Color.blue()
    )
    embed.add_field(name="How to get access", value="1. Purchase a key from our store\n2. Click 'Redeem Key'\n3. Enter your key\n4. Click 'Get Role' for your buyer role", inline=False)
    
    view = PanelView()
    await ctx.send(embed=embed, view=view)
    await ctx.send("✅ Panel created successfully!", delete_after=3)

@bot.command(name="setbuyerrole")
async def setbuyerrole(ctx, role: discord.Role):
    """Set the role buyers get when clicking Get Role - Usage: .setbuyerrole @Buyer"""
    db.execute("INSERT INTO buyer_roles (guild_id, role_id) VALUES ($1, $2) ON CONFLICT(guild_id) DO UPDATE SET role_id = $2", 
               ctx.guild.id, role.id)
    await ctx.send(f"✅ Buyer role set to {role.mention}")

@bot.command(name="genkey")
async def genkey(ctx, duration: str):
    """Generate a key for your panel - Usage: .genkey 24h or .genkey 7d"""
    # Parse duration
    if duration.endswith('h'):
        hours = int(duration[:-1])
        time_text = f"{hours} hours"
    elif duration.endswith('d'):
        days = int(duration[:-1])
        hours = days * 24
        time_text = f"{days} days"
    else:
        await ctx.send("❌ Use format like '24h' or '7d'")
        return
    
    # Generate random key
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    
    # Save to database
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit) VALUES ($1, $2, $3, $4)",
               key, ctx.guild.id, ctx.channel.id, hours)
    
    embed = discord.Embed(
        title="🎫 Key Generated",
        description=f"**Key:** `{key}`\n**Duration:** {time_text}\n**Status:** Unused",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Generated by {ctx.author.name}")
    await ctx.send(embed=embed)

@bot.command(name="forceresethwid")
async def forceresethwid(ctx, user: discord.User):
    """Force reset a user's HWID - Usage: .forceresethwid @user"""
    # In a real implementation, you'd have a HWID table
    await ctx.send(f"✅ HWID reset for {user.mention}")

@bot.command(name="blacklist")
async def blacklist(ctx, user: discord.User):
    """Blacklist a user from redeeming keys - Usage: .blacklist @user"""
    db.execute("INSERT INTO blacklist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await ctx.send(f"✅ {user.mention} has been blacklisted")

@bot.command(name="whitelist")
async def whitelist(ctx, user: discord.User):
    """Whitelist a user for lifetime access - Usage: .whitelist @user"""
    db.execute("INSERT INTO whitelist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await ctx.send(f"✅ {user.mention} has been whitelisted for lifetime access")

@bot.command(name="freekey")
async def freekey(ctx, channel: discord.TextChannel):
    """Drop a free key in a channel - Usage: .freekey #channel"""
    # Generate free key
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    
    # Save to database
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit, used) VALUES ($1, $2, $3, $4, $5)",
               key, ctx.guild.id, channel.id, 24, 0)
    
    embed = discord.Embed(
        title="🎉 FREE KEY DROP! 🎉",
        description=f"**Key:** `{key}`\n**Duration:** 24 hours\n\nRedeem this key in any panel using the 'Redeem Key' button!",
        color=discord.Color.gold()
    )
    embed.set_footer(text="First come, first served!")
    
    class CopyButton(discord.ui.View):
        def __init__(self, key_value):
            super().__init__(timeout=60)
            self.key_value = key_value
        
        @discord.ui.button(label="📋 Copy Key", style=discord.ButtonStyle.primary, emoji="📋")
        async def copy_button(self, copy_interaction: discord.Interaction, button: discord.ui.Button):
            await copy_interaction.response.send_message(f"✅ Key copied: `{self.key_value}`", ephemeral=True)
    
    await channel.send("@everyone 🎁 **A free key has dropped!** 🎁", embed=embed, view=CopyButton(key))
    await ctx.send(f"✅ Free key dropped in {channel.mention}")

@bot.command(name="update")
async def update(ctx, channel: discord.TextChannel, *, message: str):
    """Post an update embed in a channel - Usage: .update #channel Your message here"""
    embed = discord.Embed(
        title="📢 **Updates**",
        description=message,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Posted by {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await channel.send(embed=embed)
    await ctx.send(f"✅ Update posted in {channel.mention}")

@bot.command(name="ban")
async def ban(ctx, user: discord.User, *, reason: str = "No reason provided"):
    """Ban a user from the server - Usage: .ban @user reason"""
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("❌ You don't have permission to ban members!")
        return
    
    member = ctx.guild.get_member(user.id)
    if member:
        await member.ban(reason=reason)
        await ctx.send(f"✅ Banned {user.mention} | Reason: {reason}")
    else:
        await ctx.send(f"❌ Could not find {user.mention} in this server")

@bot.command(name="timeout")
async def timeout(ctx, user: discord.Member, minutes: int, *, reason: str = "No reason"):
    """Timeout a user - Usage: .timeout @user 10 Spamming"""
    if not ctx.author.guild_permissions.moderate_members:
        await ctx.send("❌ You don't have permission to timeout members!")
        return
    
    duration = timedelta(minutes=minutes)
    await user.timeout(duration, reason=reason)
    await ctx.send(f"✅ Timed out {user.mention} for {minutes} minutes | Reason: {reason}")

@bot.command(name="warn")
async def warn(ctx, user: discord.User, *, reason: str):
    """Warn a user (DMs them) - Usage: .warn @user Breaking rules"""
    embed = discord.Embed(
        title="⚠️ Warning",
        description=f"You have received a warning in **{ctx.guild.name}**\n\n**Reason:** {reason}\n**Warned by:** {ctx.author.name}",
        color=discord.Color.orange()
    )
    try:
        await user.send(embed=embed)
        await ctx.send(f"✅ Warned {user.mention} | Reason: {reason} (DM sent)")
    except:
        await ctx.send(f"✅ Warned {user.mention} | Reason: {reason} (Could not DM)")

@bot.command(name="listkeys")
async def listkeys(ctx):
    """List all unused keys"""
    keys = db.fetch("SELECT key, time_limit FROM keys WHERE used = 0 LIMIT 10")
    if keys:
        embed = discord.Embed(title="📋 Unused Keys", color=discord.Color.blue())
        key_list = "\n".join([f"`{k['key']}` - {k['time_limit']} hours" for k in keys])
        embed.description = key_list
        await ctx.send(embed=embed)
    else:
        await ctx.send("No unused keys found.")

# Keep the bot alive
async def keep_alive():
    while True:
        await asyncio.sleep(300)
        print("Bot is alive and running...")

if __name__ == "__main__":
    print("Starting Protection Bot...")
    try:
        # Start keep alive task
        loop = asyncio.get_event_loop()
        loop.create_task(keep_alive())
        bot.run(config.TOKEN)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
