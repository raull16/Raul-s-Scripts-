import discord
from discord.ext import commands
from discord import app_commands
import random
import string
import asyncio
import secrets
import aiofiles
import os
from datetime import datetime, timedelta
import config
from database import Database
import json

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents)
db = Database()

# Create scripts directory
os.makedirs('scripts', exist_ok=True)

@bot.event
async def on_ready():
    print(f'✅ Bot online! {bot.user}')
    await db.init()
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Game(name="/help"))
    print('✅ Ready!')

# ============ SLASH COMMANDS ============

@bot.tree.command(name="help", description="Show all commands")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(title="🔒 Protection Bot", color=discord.Color.blue())
    embed.add_field(name="📋 Panel", value="/setpanel <loader>\n/setbuyerrole <role>", inline=True)
    embed.add_field(name="💰 Keys", value="/genkey <duration>\n/freekey #channel\n/listkeys", inline=True)
    embed.add_field(name="📜 Script", value="/hostscript <name> (attach file)\n/viewscript <name>", inline=True)
    embed.add_field(name="👤 Users", value="/whitelist <user>\n/unwhitelist <user>\n/checkaccess <user>", inline=True)
    embed.add_field(name="🛡️ Admin", value="/ban <user>\n/timeout <user> <minutes>\n/warn <user> <reason>", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setpanel", description="Create a protection panel in current channel")
@app_commands.describe(loader="Your loader name (e.g., Luarmor V1)")
async def slash_setpanel(interaction: discord.Interaction, loader: str):
    embed = discord.Embed(
        title=f"🔒 {loader}",
        description="**Get access to our protected script!**\n\n💳 **Buy Access** - Purchase a key\n🔑 **Redeem Key** - Enter your purchased key\n📜 **Get Script** - Get your loadstring\n👑 **Get Role** - Get your buyer role",
        color=discord.Color.blue()
    )
    embed.set_footer(text="DM an admin to purchase a key")
    
    view = PanelView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Panel created!", ephemeral=True)

@bot.tree.command(name="hostscript", description="Host a script file for your panel")
@app_commands.describe(script_name="Name of your script (e.g., loader.lua)")
async def slash_hostscript(interaction: discord.Interaction, script_name: str):
    # This needs a file attachment - check if they attached one
    if not interaction.attachments:
        await interaction.response.send_message("❌ Please attach a Lua file with your command!", ephemeral=True)
        return
    
    attachment = interaction.attachments[0]
    if not attachment.filename.endswith('.lua'):
        await interaction.response.send_message("❌ Only .lua files are allowed!", ephemeral=True)
        return
    
    # Download and save the script
    file_path = f"scripts/{script_name}_{interaction.guild.id}.lua"
    await attachment.save(file_path)
    
    # Save to database
    db.execute("INSERT INTO scripts (guild_id, script_name, file_path) VALUES ($1, $2, $3) ON CONFLICT(guild_id, script_name) DO UPDATE SET file_path = $3",
               interaction.guild.id, script_name, file_path)
    
    # Get your Railway URL (you'll need to set this)
    railway_url = os.getenv('RAILWAY_URL', 'https://your-project.railway.app')
    
    embed = discord.Embed(
        title="✅ Script Hosted!",
        description=f"Script `{script_name}` has been hosted successfully!",
        color=discord.Color.green()
    )
    embed.add_field(name="📜 Loadstring", value=f"```lua\nloadstring(game:HttpGet(\"{railway_url}/getscript?guild={interaction.guild.id}&name={script_name}\"))()\n```", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="viewscript", description="View a hosted script")
@app_commands.describe(script_name="Name of the script to view")
async def slash_viewscript(interaction: discord.Interaction, script_name: str):
    script = db.fetchrow("SELECT * FROM scripts WHERE guild_id = $1 AND script_name = $2", 
                         interaction.guild.id, script_name)
    if script:
        async with aiofiles.open(script['file_path'], 'r') as f:
            content = await f.read()
            if len(content) > 1900:
                content = content[:1900] + "..."
        embed = discord.Embed(title=f"📜 {script_name}", description=f"```lua\n{content}\n```", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Script `{script_name}` not found!", ephemeral=True)

@bot.tree.command(name="genkey", description="Generate a key")
@app_commands.describe(duration="Duration (24h, 7d, 30d)")
async def slash_genkey(interaction: discord.Interaction, duration: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if duration.endswith('h'):
        hours = int(duration[:-1])
        time_text = f"{hours} hours"
    elif duration.endswith('d'):
        days = int(duration[:-1])
        hours = days * 24
        time_text = f"{days} days"
    else:
        await interaction.response.send_message("❌ Use 24h, 7d, or 30d!", ephemeral=True)
        return
    
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit) VALUES ($1, $2, $3, $4)", 
               key, interaction.guild.id, interaction.channel.id, hours)
    
    embed = discord.Embed(title="🎫 Key Generated", color=discord.Color.green())
    embed.add_field(name="Key", value=f"`{key}`", inline=False)
    embed.add_field(name="Duration", value=time_text, inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="whitelist", description="Whitelist a user for lifetime access")
@app_commands.describe(user="User to whitelist")
async def slash_whitelist(interaction: discord.Interaction, user: discord.User):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    db.execute("INSERT INTO whitelist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await interaction.response.send_message(f"✅ {user.mention} whitelisted (lifetime access)", ephemeral=True)

@bot.tree.command(name="unwhitelist", description="Remove a user from whitelist")
@app_commands.describe(user="User to remove")
async def slash_unwhitelist(interaction: discord.Interaction, user: discord.User):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    db.execute("DELETE FROM whitelist WHERE user_id = $1", user.id)
    await interaction.response.send_message(f"❌ {user.mention} removed from whitelist", ephemeral=True)

@bot.tree.command(name="checkaccess", description="Check if a user has access")
@app_commands.describe(user="User to check")
async def slash_checkaccess(interaction: discord.Interaction, user: discord.User):
    whitelisted = db.fetchrow("SELECT * FROM whitelist WHERE user_id = $1", user.id)
    key_used = db.fetchrow("SELECT * FROM keys WHERE used_by = $1 AND used = 1", user.id)
    
    if whitelisted:
        await interaction.response.send_message(f"✅ {user.mention} has **LIFETIME** access", ephemeral=True)
    elif key_used:
        await interaction.response.send_message(f"✅ {user.mention} has access (key redeemed)", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {user.mention} does NOT have access", ephemeral=True)

@bot.tree.command(name="freekey", description="Drop a free key in a channel")
@app_commands.describe(channel="Channel to drop the key in")
async def slash_freekey(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit, used) VALUES ($1, $2, $3, $4, $5)", 
               key, interaction.guild.id, channel.id, 24, 0)
    
    embed = discord.Embed(title="🎉 FREE KEY DROP!", description=f"**Key:** `{key}`\n**Duration:** 24 hours", color=discord.Color.gold())
    
    class CopyButton(discord.ui.View):
        def __init__(self, k):
            super().__init__(timeout=60)
            self.k = k
        @discord.ui.button(label="📋 Copy Key", style=discord.ButtonStyle.primary)
        async def copy(self, i, b):
            await i.response.send_message(f"✅ Key: `{self.k}`", ephemeral=True)
    
    await channel.send("@everyone 🎁 **FREE KEY DROP!**", embed=embed, view=CopyButton(key))
    await interaction.response.send_message(f"✅ Free key dropped in {channel.mention}", ephemeral=True)

@bot.tree.command(name="listkeys", description="List all unused keys")
async def slash_listkeys(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    keys = db.fetch("SELECT key, time_limit FROM keys WHERE used = 0 LIMIT 10")
    if keys:
        msg = "\n".join([f"`{k['key']}` - {k['time_limit']} hours" for k in keys])
        await interaction.response.send_message(f"📋 **Unused Keys:**\n{msg}", ephemeral=True)
    else:
        await interaction.response.send_message("No unused keys.", ephemeral=True)

@bot.tree.command(name="setbuyerrole", description="Set the role for buyers")
@app_commands.describe(role="Role to give to buyers")
async def slash_setbuyerrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    db.execute("INSERT INTO buyer_roles (guild_id, role_id) VALUES ($1, $2) ON CONFLICT(guild_id) DO UPDATE SET role_id = $2", 
               interaction.guild.id, role.id)
    await interaction.response.send_message(f"✅ Buyer role set to {role.mention}", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a user")
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def slash_ban(interaction: discord.Interaction, user: discord.User, reason: str = "No reason"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ No permission!", ephemeral=True)
        return
    member = interaction.guild.get_member(user.id)
    if member:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"✅ Banned {user.mention}", ephemeral=True)
    else:
        await interaction.response.send_message("❌ User not found", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout a user")
@app_commands.describe(user="User to timeout", minutes="Minutes to timeout", reason="Reason")
async def slash_timeout(interaction: discord.Interaction, user: discord.Member, minutes: int, reason: str = "No reason"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ No permission!", ephemeral=True)
        return
    await user.timeout(timedelta(minutes=minutes), reason=reason)
    await interaction.response.send_message(f"✅ Timed out {user.mention} for {minutes} minutes", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a user")
@app_commands.describe(user="User to warn", reason="Reason for warning")
async def slash_warn(interaction: discord.Interaction, user: discord.User, reason: str):
    embed = discord.Embed(title="⚠️ Warning", description=f"In {interaction.guild.name}\nReason: {reason}", color=discord.Color.orange())
    try:
        await user.send(embed=embed)
        await interaction.response.send_message(f"✅ Warned {user.mention}", ephemeral=True)
    except:
        await interaction.response.send_message(f"✅ Warned {user.mention} (DM failed)", ephemeral=True)

@bot.tree.command(name="update", description="Post an update in a channel")
@app_commands.describe(channel="Channel to post in", message="Update message")
async def slash_update(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    embed = discord.Embed(title="📢 Update", description=message, color=discord.Color.blue(), timestamp=datetime.now())
    embed.set_footer(text=f"Posted by {interaction.user.name}")
    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Update posted in {channel.mention}", ephemeral=True)

# ============ BUTTON PANEL ============

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
            # Get the first script for this guild
            script = db.fetchrow("SELECT script_name FROM scripts WHERE guild_id = $1 LIMIT 1", interaction.guild.id)
            railway_url = os.getenv('RAILWAY_URL', 'https://your-project.railway.app')
            
            if script:
                loadstring_url = f"{railway_url}/getscript?guild={interaction.guild.id}&name={script['script_name']}&user={interaction.user.id}"
            else:
                loadstring_url = f"{railway_url}/getscript?user={interaction.user.id}"
            
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
            role_data = db.fetchrow("SELECT role_id FROM buyer_roles WHERE guild_id = $1", interaction.guild.id)
            if role_data:
                role = interaction.guild.get_role(role_data['role_id'])
                if role:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message(f"✅ You got the {role.name} role!", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Role not found!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ No buyer role set! Use `/setbuyerrole`", ephemeral=True)
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
            
            # Get script for this guild
            script = db.fetchrow("SELECT script_name FROM scripts WHERE guild_id = $1 LIMIT 1", interaction.guild.id)
            railway_url = os.getenv('RAILWAY_URL', 'https://your-project.railway.app')
            
            if script:
                loadstring_url = f"{railway_url}/getscript?guild={interaction.guild.id}&name={script['script_name']}&user={interaction.user.id}"
            else:
                loadstring_url = f"{railway_url}/getscript?user={interaction.user.id}"
            
            embed = discord.Embed(
                title="✅ Access Granted!",
                description=f"You now have access to the script!",
                color=discord.Color.green()
            )
            embed.add_field(name="📜 Your Loadstring", value=f"```lua\nloadstring(game:HttpGet(\"{loadstring_url}\"))()\n```", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log to channel
            log_channel = discord.utils.get(interaction.guild.text_channels, name="key-logs")
            if log_channel:
                await log_channel.send(f"✅ {interaction.user} redeemed key: `{key}`")
        else:
            await interaction.response.send_message("❌ Invalid or already used key!", ephemeral=True)

# ============ UPDATE DATABASE ============

async def keep_alive():
    while True:
        await asyncio.sleep(300)
        print("Bot alive...")

if __name__ == "__main__":
    print("Starting Protection Bot...")
    loop = asyncio.get_event_loop()
    loop.create_task(keep_alive())
    bot.run(config.TOKEN)
