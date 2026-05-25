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

bot = commands.Bot(command_prefix='!', intents=intents)
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
    await bot.change_presence(activity=discord.Game(name="/setpanel to create a panel"))

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
            await interaction.response.send_message("❌ No buyer role configured! Ask an admin to run /setbuyerrole", ephemeral=True)

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

@bot.tree.command(name="setpanel", description="Create a protection panel in current channel")
@app_commands.describe(loader="Your loader name (e.g., Luarmor V1)")
async def setpanel(interaction: discord.Interaction, loader: str):
    embed = discord.Embed(
        title=f"🔒 {loader} Protection Panel",
        description="Welcome to the protection system!\n\nUse the buttons below to manage your access:",
        color=discord.Color.blue()
    )
    embed.add_field(name="How to get access", value="1. Purchase a key from our store\n2. Click 'Redeem Key'\n3. Enter your key\n4. Click 'Get Role' for your buyer role", inline=False)
    
    view = PanelView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Panel created successfully!", ephemeral=True)

@bot.tree.command(name="setbuyerrole", description="Set the role buyers get when clicking Get Role")
@app_commands.describe(role="The role to give to buyers")
async def setbuyerrole(interaction: discord.Interaction, role: discord.Role):
    db.execute("INSERT INTO buyer_roles (guild_id, role_id) VALUES ($1, $2) ON CONFLICT(guild_id) DO UPDATE SET role_id = $2", 
               interaction.guild_id, role.id)
    await interaction.response.send_message(f"✅ Buyer role set to {role.mention}", ephemeral=True)

@bot.tree.command(name="genkey", description="Generate a key for your panel")
@app_commands.describe(duration="Duration (e.g., 24h, 7d, 30d)")
async def genkey(interaction: discord.Interaction, duration: str):
    # Parse duration
    if duration.endswith('h'):
        hours = int(duration[:-1])
        time_text = f"{hours} hours"
    elif duration.endswith('d'):
        days = int(duration[:-1])
        hours = days * 24
        time_text = f"{days} days"
    else:
        await interaction.response.send_message("❌ Use format like '24h' or '7d'", ephemeral=True)
        return
    
    # Generate random key
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    
    # Save to database
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit) VALUES ($1, $2, $3, $4)",
               key, interaction.guild_id, interaction.channel_id, hours)
    
    embed = discord.Embed(
        title="🎫 Key Generated",
        description=f"**Key:** `{key}`\n**Duration:** {time_text}\n**Status:** Unused",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Generated by {interaction.user.name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="forceresethwid", description="Force reset a user's HWID")
@app_commands.describe(user="The user to reset HWID for")
async def forceresethwid(interaction: discord.Interaction, user: discord.User):
    # In a real implementation, you'd have a HWID table
    await interaction.response.send_message(f"✅ HWID reset for {user.mention}", ephemeral=True)

@bot.tree.command(name="blacklist", description="Blacklist a user from redeeming keys")
@app_commands.describe(user="The user to blacklist")
async def blacklist(interaction: discord.Interaction, user: discord.User):
    db.execute("INSERT INTO blacklist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await interaction.response.send_message(f"✅ {user.mention} has been blacklisted", ephemeral=True)

@bot.tree.command(name="whitelist", description="Whitelist a user for lifetime access")
@app_commands.describe(user="The user to whitelist")
async def whitelist(interaction: discord.Interaction, user: discord.User):
    db.execute("INSERT INTO whitelist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await interaction.response.send_message(f"✅ {user.mention} has been whitelisted for lifetime access", ephemeral=True)

@bot.tree.command(name="freekey", description="Drop a free key in a channel")
@app_commands.describe(channel="The channel to drop the key in")
async def freekey(interaction: discord.Interaction, channel: discord.TextChannel):
    # Generate free key
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    
    # Save to database
    db.execute("INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit, used) VALUES ($1, $2, $3, $4, $5)",
               key, interaction.guild_id, channel.id, 24, 0)
    
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
    await interaction.response.send_message(f"✅ Free key dropped in {channel.mention}", ephemeral=True)

@bot.tree.command(name="update", description="Post an update embed in a channel")
@app_commands.describe(channel="The channel to post in", message="The update message")
async def update(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    embed = discord.Embed(
        title="📢 **Updates**",
        description=message,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Posted by {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Update posted in {channel.mention}", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a user from the server")
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ You don't have permission to ban members!", ephemeral=True)
        return
    
    member = interaction.guild.get_member(user.id)
    if member:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"✅ Banned {user.mention} | Reason: {reason}", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Could not find {user.mention} in this server", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout a user")
@app_commands.describe(user="User to timeout", minutes="Minutes to timeout", reason="Reason")
async def timeout(interaction: discord.Interaction, user: discord.Member, minutes: int, reason: str = "No reason"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ You don't have permission to timeout members!", ephemeral=True)
        return
    
    duration = timedelta(minutes=minutes)
    await user.timeout(duration, reason=reason)
    await interaction.response.send_message(f"✅ Timed out {user.mention} for {minutes} minutes | Reason: {reason}", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a user (DMs them)")
@app_commands.describe(user="User to warn", reason="Reason for warning")
async def warn(interaction: discord.Interaction, user: discord.User, reason: str):
    embed = discord.Embed(
        title="⚠️ Warning",
        description=f"You have received a warning in **{interaction.guild.name}**\n\n**Reason:** {reason}\n**Warned by:** {interaction.user.name}",
        color=discord.Color.orange()
    )
    try:
        await user.send(embed=embed)
        await interaction.response.send_message(f"✅ Warned {user.mention} | Reason: {reason} (DM sent)", ephemeral=True)
    except:
        await interaction.response.send_message(f"✅ Warned {user.mention} | Reason: {reason} (Could not DM)", ephemeral=True)

@bot.tree.command(name="listkeys", description="List all unused keys")
async def listkeys(interaction: discord.Interaction):
    keys = db.fetch("SELECT key, time_limit FROM keys WHERE used = 0 LIMIT 10")
    if keys:
        embed = discord.Embed(title="📋 Unused Keys", color=discord.Color.blue())
        key_list = "\n".join([f"`{k['key']}` - {k['time_limit']} hours" for k in keys])
        embed.description = key_list
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("No unused keys found.", ephemeral=True)

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
