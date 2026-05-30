import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
from datetime import datetime

import config
from database import init_db, get_channels, set_channels, remove_guild
from websocket_handler import WebSocketHandler
from webhook_manager import WebhookManager
from embeds import create_finding_embed, create_status_embed, create_config_embed

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

class VexisFinderBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.ws_handler = None
        self.webhook_manager = WebhookManager()
    
    async def setup_hook(self):
        await self.webhook_manager.init_session()
        await self.tree.sync()
        logger.info("Commands synced!")
    
    async def on_ready(self):
        init_db()
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.start_websocket()
    
    async def start_websocket(self):
        async def on_ws_message(data):
            # Process incoming WebSocket data
            await self.process_finding(data)
        
        self.ws_handler = WebSocketHandler(config.WEBSOCKET_URL, on_ws_message)
        await self.ws_handler.connect()
        logger.info("WebSocket handler started")
    
    async def process_finding(self, data):
        """Process a finding and send to all configured channels"""
        # Expected data format - adapt to your WebSocket's actual format
        # This handles multiple possible formats
        finding = None
        
        if isinstance(data, dict):
            # Case 1: Direct finding object
            if "name" in data and "value" in data:
                finding = data
            # Case 2: Findings array
            elif "findings" in data and isinstance(data["findings"], list):
                for f in data["findings"]:
                    await self.process_finding(f)
                return
            # Case 3: Nested structure
            elif "data" in data and isinstance(data["data"], dict):
                finding = data["data"]
        
        if not finding:
            logger.debug(f"Skipping non-finding message: {data}")
            return
        
        # Add timestamp if missing
        if "timestamp" not in finding:
            finding["timestamp"] = int(datetime.now().timestamp())
        
        # Set default tier if missing
        if "tier" not in finding:
            finding["tier"] = "Highlights" if finding.get("value", 0) > 50000 else "Midlights"
        
        # Create embed
        embed = create_finding_embed(finding)
        
        # Send to all guilds that have configured channels
        for guild in self.guilds:
            channel_ids = get_channels(guild.id)
            if channel_ids:
                # Refresh webhooks if needed
                if guild.id not in self.webhook_manager.webhooks or len(self.webhook_manager.webhooks[guild.id]) != len(channel_ids):
                    await self.webhook_manager.refresh_webhooks(guild, channel_ids)
                
                await self.webhook_manager.send_to_all_webhooks(guild.id, embed)
        
        logger.info(f"Sent finding: {finding.get('name')} - {finding.get('value')}")
    
    async def close(self):
        if self.ws_handler:
            await self.ws_handler.disconnect()
        await self.webhook_manager.close_session()
        await super().close()

bot = VexisFinderBot()

# ============= SLASH COMMANDS =============

@bot.tree.command(name="setch", description="Set channels for Vexis Finder notifications (creates webhooks)")
@app_commands.describe(channel1="First channel", channel2="Second channel", channel3="Third channel")
async def setch(interaction: discord.Interaction, channel1: discord.TextChannel, channel2: discord.TextChannel = None, channel3: discord.TextChannel = None):
    """Set up to 3 channels to receive Vexis Finder notifications"""
    
    # Check permissions
    for ch in [channel1, channel2, channel3]:
        if ch:
            perms = ch.permissions_for(interaction.guild.me)
            if not perms.manage_webhooks or not perms.send_messages:
                await interaction.response.send_message(f"❌ Missing permissions in {ch.mention}. Need `Manage Webhooks` and `Send Messages`.", ephemeral=True)
                return
    
    channels = [ch.id for ch in [channel1, channel2, channel3] if ch]
    
    if not channels:
        await interaction.response.send_message("❌ Please specify at least one channel!", ephemeral=True)
        return
    
    # Save to database
    set_channels(interaction.guild_id, channels)
    
    # Create webhooks
    webhooks = await bot.webhook_manager.refresh_webhooks(interaction.guild, channels)
    
    embed = create_config_embed(channels)
    embed.add_field(name="✅ Status", value=f"Created {len(webhooks)} webhook(s) successfully!", inline=False)
    
    await interaction.response.send_message(embed=embed)
    logger.info(f"Configured guild {interaction.guild_id} with channels {channels}")

@bot.tree.command(name="reconnect", description="Reconnect to the Vexis Finder WebSocket")
async def reconnect_ws(interaction: discord.Interaction):
    """Force a reconnection to the WebSocket"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        if bot.ws_handler:
            await bot.ws_handler.reconnect()
            embed = create_status_embed(
                "🔄 WebSocket Reconnected",
                "Successfully reconnected to the Vexis Finder WebSocket!\nAll logs will now be received again.",
                is_error=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await bot.start_websocket()
            embed = create_status_embed(
                "🔌 WebSocket Started",
                "WebSocket connection has been established.",
                is_error=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        embed = create_status_embed(
            "❌ Reconnection Failed",
            f"Error: {str(e)[:100]}",
            is_error=True
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.error(f"Reconnect error: {e}")

@bot.tree.command(name="status", description="Check Vexis Finder bot status")
async def status(interaction: discord.Interaction):
    """Check the status of the bot and WebSocket connection"""
    channels = get_channels(interaction.guild_id)
    
    ws_status = "🟢 Connected" if bot.ws_handler and bot.ws_handler.websocket else "🔴 Disconnected"
    ws_status += " (Auto-reconnecting)" if bot.ws_handler and bot.ws_handler._running else ""
    
    embed = discord.Embed(
        title="📊 Vexis Finder Status",
        description=f"**WebSocket:** {ws_status}\n**Configured Channels:** {len(channels)}\n**Guilds:** {len(bot.guilds)}",
        color=0xD4AF37
    )
    
    if channels:
        channel_mentions = ", ".join([f"<#{ch}>" for ch in channels])
        embed.add_field(name="📡 Active Channels", value=channel_mentions, inline=False)
    
    embed.set_footer(text="Vexis Finder • Black & Gold Edition")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="test", description="Send a test embed to configured channels")
async def test_notification(interaction: discord.Interaction):
    """Send a test notification to all configured channels"""
    channels = get_channels(interaction.guild_id)
    
    if not channels:
        await interaction.response.send_message("❌ No channels configured. Use `/setch` first!", ephemeral=True)
        return
    
    test_data = {
        "name": "🐉 TEST PET - Hydra Dragon",
        "value": 1234567,
        "tier": "Highlights",
        "job_id": "test_job_12345",
        "timestamp": int(datetime.now().timestamp())
    }
    
    embed = create_finding_embed(test_data)
    embed.description = "**TEST NOTIFICATION**\n" + embed.description
    
    await bot.webhook_manager.refresh_webhooks(interaction.guild, channels)
    await bot.webhook_manager.send_to_all_webhooks(interaction.guild_id, embed)
    
    await interaction.response.send_message(f"✅ Test notification sent to {len(channels)} channel(s)!", ephemeral=True)

@bot.tree.command(name="removech", description="Remove all configured channels for this server")
async def remove_channels(interaction: discord.Interaction):
    """Remove all channel configurations for this server"""
    channels = get_channels(interaction.guild_id)
    
    if not channels:
        await interaction.response.send_message("❌ No channels are currently configured!", ephemeral=True)
        return
    
    # Remove from database
    remove_guild(interaction.guild_id)
    
    # Clean up webhooks
    if interaction.guild_id in bot.webhook_manager.webhooks:
        for wh in bot.webhook_manager.webhooks[interaction.guild_id]:
            try:
                await wh.delete()
            except:
                pass
        del bot.webhook_manager.webhooks[interaction.guild_id]
    
    embed = create_status_embed(
        "🗑️ Configuration Removed",
        f"Removed {len(channels)} configured channel(s). No more notifications will be sent.",
        is_error=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============= RUN THE BOT =============
if __name__ == "__main__":
    try:
        bot.run(config.TOKEN)
    except KeyboardInterrupt:
        print("Bot shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
