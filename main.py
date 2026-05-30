import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import sqlite3
import os
import websockets
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
import logging
from threading import Thread
from flask import Flask

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask web server for Railway keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Vexis Finder Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Start web server in a separate thread
Thread(target=run_web_server, daemon=True).start()
logger.info("Web server started on port 8080")

# Config
TOKEN = os.environ.get("TOKEN")
WEBSOCKET_URL = "wss://join.signorefinderws.org/ws"

if not TOKEN:
    raise ValueError("TOKEN environment variable not set")

# Database setup
DB_PATH = "vexis_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guild_configs (
            guild_id INTEGER PRIMARY KEY,
            channel_ids TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_channels(guild_id: int) -> List[int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_ids FROM guild_configs WHERE guild_id = ?", (guild_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def set_channels(guild_id: int, channel_ids: List[int]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO guild_configs (guild_id, channel_ids) VALUES (?, ?)",
                   (guild_id, json.dumps(channel_ids)))
    conn.commit()
    conn.close()

def remove_guild(guild_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM guild_configs WHERE guild_id = ?", (guild_id,))
    conn.commit()
    conn.close()

# Embed colors (Black & Gold)
GOLD = 0xD4AF37
DARK_GOLD = 0xB8860B

def format_value(value):
    value = value or 0
    if value >= 1000000:
        return f"{value/1000000:.1f}M"
    elif value >= 1000:
        return f"{value/1000:.1f}K"
    return str(value)

def create_finding_embed(data: dict) -> discord.Embed:
    pet_name = data.get("name", "Unknown")
    value = data.get("value", 0)
    tier = data.get("tier", "Midlights")
    
    embed = discord.Embed(
        title="🔍 **VEXIS FINDER**",
        description=f"**{pet_name}** has been detected!",
        color=GOLD,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💰 Value", value=f"`{format_value(value)} Coins`", inline=True)
    embed.add_field(name="🏷️ Tier", value=f"`{tier}`", inline=True)
    embed.add_field(name="📊 Rarity", value="`🔴 High`" if tier == "Highlights" else "`🟡 Mid`", inline=True)
    
    embed.set_footer(text="Vexis Finder • Real-time Pet Notifier")
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")
    
    return embed

# Bot class
class VexisFinderBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)
        self.ws_task = None
        self.ws = None
        self.session = None
        self._running = True
    
    async def setup_hook(self):
        await self.tree.sync()
        self.session = aiohttp.ClientSession()
        init_db()
        logger.info("Bot setup complete")
    
    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        # Start WebSocket connection in background
        asyncio.create_task(self.websocket_loop())
    
    async def websocket_loop(self):
        """Main WebSocket connection loop with auto-reconnect"""
        while self._running:
            try:
                logger.info(f"Connecting to WebSocket: {WEBSOCKET_URL}")
                async with websockets.connect(
                    WEBSOCKET_URL, 
                    ping_interval=20, 
                    ping_timeout=10,
                    close_timeout=5
                ) as ws:
                    self.ws = ws
                    logger.info("✅ WebSocket connected!")
                    
                    # Listen for messages
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            logger.info(f"📨 Received: {data}")
                            await self.process_finding(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON: {message}")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️ WebSocket disconnected, reconnecting...")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            
            # Wait before reconnecting
            if self._running:
                await asyncio.sleep(5)
    
    async def process_finding(self, data):
        """Process incoming WebSocket data and send to channels"""
        # Handle different data formats
        finding = None
        
        if isinstance(data, dict):
            # Direct finding object
            if "name" in data and "value" in data:
                finding = data
            # Findings array
            elif "findings" in data and isinstance(data["findings"], list):
                for f in data["findings"]:
                    await self.process_finding(f)
                return
            # Nested data
            elif "data" in data and isinstance(data["data"], dict):
                finding = data["data"]
        
        if not finding:
            logger.debug(f"Skipping non-finding message: {data}")
            return
        
        # Set default tier if missing
        if "tier" not in finding:
            finding["tier"] = "Highlights" if finding.get("value", 0) > 50000 else "Midlights"
        
        # Add timestamp if missing
        if "timestamp" not in finding:
            finding["timestamp"] = int(datetime.now().timestamp())
        
        # Create embed
        embed = create_finding_embed(finding)
        
        # Send to all configured guilds
        for guild in self.guilds:
            channel_ids = get_channels(guild.id)
            if channel_ids:
                await self.send_to_channels(guild, channel_ids, embed)
    
    async def send_to_channels(self, guild: discord.Guild, channel_ids: List[int], embed: discord.Embed):
        """Send embed to all configured channels using webhooks"""
        for channel_id in channel_ids:
            channel = guild.get_channel(channel_id)
            if channel and isinstance(channel, (discord.TextChannel, discord.Thread)):
                try:
                    # Check for existing webhook
                    webhooks = await channel.webhooks()
                    webhook = None
                    for wh in webhooks:
                        if wh.name == "VexisFinder":
                            webhook = wh
                            break
                    
                    # Create new webhook if none exists
                    if not webhook:
                        webhook = await channel.create_webhook(name="VexisFinder")
                    
                    # Send the embed
                    await webhook.send(embed=embed, username="Vexis Finder")
                    logger.info(f"✅ Sent to #{channel.name}")
                    
                except discord.Forbidden:
                    logger.error(f"❌ No permission to send to #{channel.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to send to #{channel.name}: {e}")
    
    async def reconnect_websocket(self):
        """Force reconnect the WebSocket"""
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
        # The loop will auto-reconnect
        logger.info("🔄 Manual reconnect triggered")
    
    async def close(self):
        self._running = False
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
        if self.session:
            await self.session.close()
        await super().close()

bot = VexisFinderBot()

# ============= SLASH COMMANDS =============

@bot.tree.command(name="setch", description="Set channels for Vexis Finder notifications")
@app_commands.describe(
    channel1="First channel",
    channel2="Second channel (optional)",
    channel3="Third channel (optional)"
)
async def setch(
    interaction: discord.Interaction,
    channel1: discord.TextChannel,
    channel2: Optional[discord.TextChannel] = None,
    channel3: Optional[discord.TextChannel] = None
):
    channels = [ch for ch in [channel1, channel2, channel3] if ch]
    
    # Check permissions
    for ch in channels:
        perms = ch.permissions_for(interaction.guild.me)
        if not perms.manage_webhooks or not perms.send_messages:
            await interaction.response.send_message(
                f"❌ Missing permissions in {ch.mention}. Need `Manage Webhooks` and `Send Messages`.",
                ephemeral=True
            )
            return
    
    # Save to database
    set_channels(interaction.guild_id, [ch.id for ch in channels])
    
    embed = discord.Embed(
        title="⚙️ Vexis Finder Configuration",
        description=f"**Configured Channels:**\n" + "\n".join([f"• {ch.mention}" for ch in channels]),
        color=GOLD
    )
    embed.add_field(name="✅ Status", value=f"Set {len(channels)} channel(s) successfully!", inline=False)
    embed.set_footer(text="Vexis Finder • Black & Gold Edition")
    
    await interaction.response.send_message(embed=embed)
    logger.info(f"Configured guild {interaction.guild_id} with channels {[ch.id for ch in channels]}")

@bot.tree.command(name="reconnect", description="Reconnect to the Vexis Finder WebSocket")
async def reconnect_ws(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await bot.reconnect_websocket()
        embed = discord.Embed(
            title="🔄 WebSocket Reconnected",
            description="Successfully reconnected to the Vexis Finder WebSocket!",
            color=GOLD
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Reconnection Failed",
            description=f"Error: {str(e)[:100]}",
            color=DARK_GOLD
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="status", description="Check Vexis Finder bot status")
async def status(interaction: discord.Interaction):
    channels = get_channels(interaction.guild_id)
    
    # Check WebSocket status
    ws_connected = bot.ws and not getattr(bot.ws, 'closed', True)
    ws_status = "🟢 Connected" if ws_connected else "🔴 Disconnected"
    
    embed = discord.Embed(
        title="📊 Vexis Finder Status",
        description=f"**WebSocket:** {ws_status}\n**Configured Channels:** {len(channels)}\n**Guilds:** {len(bot.guilds)}",
        color=GOLD
    )
    
    if channels:
        channel_mentions = ", ".join([f"<#{ch}>" for ch in channels])
        embed.add_field(name="📡 Active Channels", value=channel_mentions, inline=False)
    
    embed.set_footer(text="Vexis Finder • Black & Gold Edition")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="test", description="Send a test notification to configured channels")
async def test_notification(interaction: discord.Interaction):
    channels = get_channels(interaction.guild_id)
    
    if not channels:
        await interaction.response.send_message("❌ No channels configured. Use `/setch` first!", ephemeral=True)
        return
    
    test_data = {
        "name": "🐉 TEST PET - Hydra Dragon",
        "value": 1234567,
        "tier": "Highlights"
    }
    
    embed = create_finding_embed(test_data)
    embed.description = "**🧪 TEST NOTIFICATION**\n" + embed.description
    
    await interaction.response.send_message(f"✅ Sending test notification to {len(channels)} channel(s)...", ephemeral=True)
    
    for channel_id in channels:
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            try:
                webhooks = await channel.webhooks()
                webhook = None
                for wh in webhooks:
                    if wh.name == "VexisFinder":
                        webhook = wh
                        break
                if not webhook:
                    webhook = await channel.create_webhook(name="VexisFinder")
                await webhook.send(embed=embed, username="Vexis Finder")
                logger.info(f"Test sent to #{channel.name}")
            except Exception as e:
                logger.error(f"Test failed for {channel.name}: {e}")

@bot.tree.command(name="removech", description="Remove all configured channels for this server")
async def remove_channels(interaction: discord.Interaction):
    channels = get_channels(interaction.guild_id)
    
    if not channels:
        await interaction.response.send_message("❌ No channels are currently configured!", ephemeral=True)
        return
    
    remove_guild(interaction.guild_id)
    
    embed = discord.Embed(
        title="🗑️ Configuration Removed",
        description=f"Removed {len(channels)} configured channel(s). No more notifications will be sent.",
        color=GOLD
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============= RUN THE BOT =============
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("Bot shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
