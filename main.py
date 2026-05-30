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
    # Defer immediately to prevent timeout
    await interaction.response.defer(ephemeral=True)
    
    channels = [ch for ch in [channel1, channel2, channel3] if ch]
    
    # Check permissions
    for ch in channels:
        perms = ch.permissions_for(interaction.guild.me)
        if not perms.manage_webhooks or not perms.send_messages:
            await interaction.followup.send(
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
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    logger.info(f"Configured guild {interaction.guild_id}")

@bot.tree.command(name="removech", description="Remove all configured channels for this server")
async def remove_channels(interaction: discord.Interaction):
    # Defer immediately
    await interaction.response.defer(ephemeral=True)
    
    channels = get_channels(interaction.guild_id)
    
    if not channels:
        await interaction.followup.send("❌ No channels are currently configured!", ephemeral=True)
        return
    
    remove_guild(interaction.guild_id)
    
    embed = discord.Embed(
        title="🗑️ Configuration Removed",
        description=f"Removed {len(channels)} configured channel(s). No more notifications will be sent.",
        color=GOLD
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="status", description="Check Vexis Finder bot status")
async def status(interaction: discord.Interaction):
    # Defer immediately
    await interaction.response.defer(ephemeral=True)
    
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
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="test", description="Send a test notification to configured channels")
async def test_notification(interaction: discord.Interaction):
    # Defer immediately
    await interaction.response.defer(ephemeral=True)
    
    channels = get_channels(interaction.guild_id)
    
    if not channels:
        await interaction.followup.send("❌ No channels configured. Use `/setch` first!", ephemeral=True)
        return
    
    test_data = {
        "name": "🐉 TEST PET - Hydra Dragon",
        "value": 1234567,
        "tier": "Highlights"
    }
    
    embed = create_finding_embed(test_data)
    embed.description = "**🧪 TEST NOTIFICATION**\n" + embed.description
    
    await interaction.followup.send(f"✅ Sending test notification to {len(channels)} channel(s)...", ephemeral=True)
    
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
