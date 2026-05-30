import discord
from discord import Webhook, AsyncWebhookAdapter
import aiohttp
from typing import Dict, List, Optional

class WebhookManager:
    def __init__(self):
        self.webhooks: Dict[int, List[discord.Webhook]] = {}  # guild_id -> list of webhooks
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def init_session(self):
        self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def create_webhooks_for_channels(self, guild: discord.Guild, channel_ids: List[int]) -> List[discord.Webhook]:
        """Create webhooks for given channels and store them"""
        created_webhooks = []
        
        for channel_id in channel_ids:
            channel = guild.get_channel(channel_id)
            if not channel or not isinstance(channel, (discord.TextChannel, discord.Thread)):
                continue
            
            try:
                # Check if a webhook named "VexisFinder" already exists
                existing_webhooks = await channel.webhooks()
                vexis_webhook = None
                for wh in existing_webhooks:
                    if wh.name == "VexisFinder":
                        vexis_webhook = wh
                        break
                
                if vexis_webhook:
                    created_webhooks.append(vexis_webhook)
                else:
                    # Create a new webhook
                    webhook = await channel.create_webhook(name="VexisFinder", reason="Vexis Finder Bot - Logging")
                    created_webhooks.append(webhook)
                    
            except discord.Forbidden:
                print(f"No permission to create webhook in {channel.name}")
            except Exception as e:
                print(f"Error creating webhook in {channel.name}: {e}")
        
        self.webhooks[guild.id] = created_webhooks
        return created_webhooks
    
    async def send_to_all_webhooks(self, guild_id: int, embed: discord.Embed):
        """Send an embed to all webhooks for a guild"""
        webhooks = self.webhooks.get(guild_id, [])
        for webhook in webhooks:
            try:
                await webhook.send(embed=embed, username="Vexis Finder", avatar_url="https://i.imgur.com/8Km9tLL.png")
            except Exception as e:
                print(f"Error sending via webhook: {e}")
    
    async def refresh_webhooks(self, guild: discord.Guild, channel_ids: List[int]):
        """Refresh webhooks for a guild (remove old, create new)"""
        # Delete old webhooks owned by this bot
        old_webhooks = self.webhooks.get(guild.id, [])
        for wh in old_webhooks:
            try:
                await wh.delete()
            except:
                pass
        
        # Create new ones
        return await self.create_webhooks_for_channels(guild, channel_ids)
