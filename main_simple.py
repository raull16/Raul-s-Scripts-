import discord
from discord.ext import commands
import config
import traceback

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot is online! Logged in as {bot.user}")
    print(f"✅ Bot is in {len(bot.guilds)} guilds")
    
    # Try to sync commands
    try:
        await bot.tree.sync()
        print("✅ Commands synced successfully!")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.tree.command(name="ping", description="Check if bot is working")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🏓")

if __name__ == "__main__":
    print("Starting bot...")
    try:
        bot.run(config.TOKEN)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
