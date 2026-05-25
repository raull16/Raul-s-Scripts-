import discord
from discord.ext import commands
from discord import app_commands
import random
import string
import asyncio
from datetime import datetime, timedelta
import config
from database import Database

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
db = Database()

# Store active panels in memory
active_panels = {}

class PanelView(discord.ui.View):
    def __init__(self, guild_id, channel_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.channel_id = channel_id
    
    @discord.ui.button(label="🔑 Redeem Key", style=discord.ButtonStyle.primary, custom_id="redeem_key")
    async def redeem_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemModal(self.guild_id, self.channel_id))
    
    @discord.ui.button(label="🔄 Reset HWID", style=discord.ButtonStyle.secondary, custom_id="reset_hwid")
    async def reset_hwid_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Logic to reset HWID
        await interaction.response.send_message("✅ Your HWID has been reset!", ephemeral=True)
    
    @discord.ui.button(label="📜 Get Script", style=discord.ButtonStyle.success, custom_id="get_script")
    async def script_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Logic to deliver script
        await interaction.response.send_message("Here's your script: `loader.lua`", ephemeral=True)
    
    @discord.ui.button(label="👑 Get Role", style=discord.ButtonStyle.danger, custom_id="get_role")
    async def role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get buyer role from database
        async with db.pool.acquire() as conn:
            role_data = await conn.fetchrow("SELECT role_id FROM buyer_roles WHERE guild_id = $1", self.guild_id)
            if role_data:
                role = interaction.guild.get_role(role_data['role_id'])
                if role:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message(f"✅ You've been given the {role.name} role!", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Role not found!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ No buyer role configured!", ephemeral=True)

class RedeemModal(discord.ui.Modal):
    def __init__(self, guild_id, channel_id):
        super().__init__(title="Redeem Key")
        self.guild_id = guild_id
        self.channel_id = channel_id
        
        self.key_input = discord.ui.TextInput(
            label="Enter your key:",
            placeholder="XXXX-XXXX-XXXX-XXXX",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.key_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value
        async with db.pool.acquire() as conn:
            # Check if user is blacklisted
            blacklisted = await conn.fetchrow("SELECT * FROM blacklist WHERE user_id = $1", interaction.user.id)
            if blacklisted:
                await interaction.response.send_message("❌ You are blacklisted!", ephemeral=True)
                return
            
            # Check if user is whitelisted (lifetime)
            whitelisted = await conn.fetchrow("SELECT * FROM whitelist WHERE user_id = $1", interaction.user.id)
            if whitelisted:
                await interaction.response.send_message("✅ You're whitelisted! Access granted permanently.", ephemeral=True)
                return
            
            # Check key
            key_data = await conn.fetchrow("SELECT * FROM keys WHERE key = $1 AND used = FALSE", key)
            if key_data:
                await conn.execute("UPDATE keys SET used = TRUE, used_by = $1 WHERE key = $2", interaction.user.id, key)
                await interaction.response.send_message("✅ Key redeemed successfully! You now have access.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Invalid or already used key!", ephemeral=True)

@bot.event
async def on_ready():
    await db.init()
    await bot.tree.sync()
    print(f'Bot is ready! Logged in as {bot.user}')

@bot.tree.command(name="setpanel", description="Set up a protection panel in the current channel")
@app_commands.describe(loader="Loader name or version")
async def setpanel(interaction: discord.Interaction, loader: str):
    embed = discord.Embed(
        title=f"🔒 {loader} Protection Panel",
        description="Welcome to the protection system! Use the buttons below:",
        color=discord.Color.blue()
    )
    view = PanelView(interaction.guild_id, interaction.channel_id)
    await interaction.channel.send(embed=embed, view=view)
    
    # Store panel info in database
    async with db.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO panels (guild_id, channel_id, panel_data) VALUES ($1, $2, $3) ON CONFLICT (guild_id, channel_id) DO UPDATE SET panel_data = $3",
            interaction.guild_id, interaction.channel_id, {"loader": loader, "created_by": interaction.user.id}
        )
    
    await interaction.response.send_message("✅ Panel created successfully!", ephemeral=True)

@bot.tree.command(name="setbuyerrole", description="Set the role that buyers get when clicking 'Get Role'")
@app_commands.describe(role="The role to give to buyers")
async def setbuyerrole(interaction: discord.Interaction, role: discord.Role):
    async with db.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO buyer_roles (guild_id, role_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET role_id = $2",
            interaction.guild_id, role.id
        )
    await interaction.response.send_message(f"✅ Buyer role set to {role.mention}", ephemeral=True)

@bot.tree.command(name="forceresethwid", description="Force reset a user's HWID")
@app_commands.describe(user="The user to reset HWID for")
async def forceresethwid(interaction: discord.Interaction, user: discord.User):
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM hwids WHERE user_id = $1", user.id)
    await interaction.response.send_message(f"✅ HWID reset for {user.mention}", ephemeral=True)

@bot.tree.command(name="genkey", description="Generate a key for any panel")
@app_commands.describe(amt="Amount of time (in hours/days - specify like 24h or 7d)")
async def genkey(interaction: discord.Interaction, amt: str):
    # Parse time
    if amt.endswith('h'):
        hours = int(amt[:-1])
        time_text = f"{hours} hours"
    elif amt.endswith('d'):
        days = int(amt[:-1])
        hours = days * 24
        time_text = f"{days} days"
    else:
        await interaction.response.send_message("❌ Use format like '24h' or '7d'", ephemeral=True)
        return
    
    # Generate random key
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    
    async with db.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit) VALUES ($1, $2, $3, $4)",
            key, interaction.guild_id, interaction.channel_id, hours
        )
    
    embed = discord.Embed(
        title="🎫 Key Generated",
        description=f"**Key:** `{key}`\n**Duration:** {time_text}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="blacklist", description="Blacklist a user from redeeming keys")
@app_commands.describe(user="The user to blacklist")
async def blacklist(interaction: discord.Interaction, user: discord.User):
    async with db.pool.acquire() as conn:
        await conn.execute("INSERT INTO blacklist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await interaction.response.send_message(f"✅ {user.mention} has been blacklisted", ephemeral=True)

@bot.tree.command(name="whitelist", description="Whitelist a user for lifetime access")
@app_commands.describe(user="The user to whitelist")
async def whitelist(interaction: discord.Interaction, user: discord.User):
    async with db.pool.acquire() as conn:
        await conn.execute("INSERT INTO whitelist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
    await interaction.response.send_message(f"✅ {user.mention} has been whitelisted for lifetime access", ephemeral=True)

@bot.tree.command(name="freekey", description="Drop a free key in a channel")
@app_commands.describe(channel="The channel to drop the key in")
async def freekey(interaction: discord.Interaction, channel: discord.TextChannel):
    # Generate free key
    key = '-'.join(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4))
    
    async with db.pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO keys (key, panel_guild_id, panel_channel_id, time_limit, used) VALUES ($1, $2, $3, $4, $5)",
            key, interaction.guild_id, channel.id, 24, False
        )
    
    embed = discord.Embed(
        title="🎉 FREE KEY DROP! 🎉",
        description=f"**Key:** `{key}`\n**Duration:** 24 hours\n\nRedeem this key in any panel!",
        color=discord.Color.gold()
    )
    
    class CopyButton(discord.ui.View):
        @discord.ui.button(label="📋 Copy Key", style=discord.ButtonStyle.primary)
        async def copy_button(self, interaction_copy: discord.Interaction, button: discord.ui.Button):
            await interaction_copy.response.send_message(f"✅ Key copied: `{key}`", ephemeral=True)
    
    await channel.send("@everyone A free key has now dropped! Redeem this key in any panel.", embed=embed, view=CopyButton())
    await interaction.response.send_message(f"✅ Free key dropped in {channel.mention}", ephemeral=True)

@bot.tree.command(name="update", description="Post an update in a channel")
@app_commands.describe(channel="The channel to post the update in", message="The update message")
async def update(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    embed = discord.Embed(
        title="📢 Updates",
        description=message,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Posted by {interaction.user.name}")
    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Update posted in {channel.mention}", ephemeral=True)

# Moderation commands
@bot.tree.command(name="ban", description="Ban a user from the server")
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    
    await interaction.guild.ban(user, reason=reason)
    await interaction.response.send_message(f"✅ Banned {user.mention} | Reason: {reason}", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout a user")
@app_commands.describe(user="User to timeout", minutes="Minutes to timeout", reason="Reason")
async def timeout(interaction: discord.Interaction, user: discord.Member, minutes: int, reason: str = "No reason"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    
    duration = timedelta(minutes=minutes)
    await user.timeout(duration, reason=reason)
    await interaction.response.send_message(f"✅ Timed out {user.mention} for {minutes} minutes", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a user")
@app_commands.describe(user="User to warn", reason="Reason for warning")
async def warn(interaction: discord.Interaction, user: discord.User, reason: str):
    embed = discord.Embed(title="⚠️ Warning", description=f"You have been warned in {interaction.guild.name}\n**Reason:** {reason}", color=discord.Color.orange())
    try:
        await user.send(embed=embed)
    except:
        pass
    await interaction.response.send_message(f"✅ Warned {user.mention} | Reason: {reason}", ephemeral=True)

bot.run(config.TOKEN)
