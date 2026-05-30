import discord
from datetime import datetime

# Black & Gold Theme
BLACK = 0x0A0A0A
GOLD = 0xD4AF37
DARK_GOLD = 0xB8860B

def create_finding_embed(data: dict) -> discord.Embed:
    """
    Creates a black & gold embed for a finding.
    Expected data format:
    {
        "id": str,
        "name": str,
        "value": int/float,
        "tier": str (Highlights/Midlights),
        "job_id": str (optional),
        "base_name": str (optional),
        "timestamp": int (optional)
    }
    """
    pet_name = data.get("name", "Unknown")
    value = data.get("value", 0)
    tier = data.get("tier", "Midlights")
    job_id = data.get("job_id", "")
    timestamp = data.get("timestamp", int(datetime.now().timestamp()))
    
    # Format value with K/M suffix
    if value >= 1_000_000:
        formatted_value = f"{value/1_000_000:.1f}M"
    elif value >= 1_000:
        formatted_value = f"{value/1_000:.1f}K"
    else:
        formatted_value = str(value)
    
    embed = discord.Embed(
        title=f"🔍 **VEXIS FINDER**",
        description=f"**{pet_name}** has been detected!",
        color=GOLD,
        timestamp=datetime.fromtimestamp(timestamp)
    )
    
    embed.add_field(name="💰 Value", value=f"`{formatted_value} Coins`", inline=True)
    embed.add_field(name="🏷️ Tier", value=f"`{tier}`", inline=True)
    embed.add_field(name="📊 Rarity", value="`🔴 High`" if tier == "Highlights" else "`🟡 Mid`", inline=True)
    
    if job_id and job_id != "":
        embed.add_field(name="🔗 Job ID", value=f"`{job_id[:20]}...`" if len(job_id) > 20 else f"`{job_id}`", inline=False)
    
    embed.set_footer(text="Vexis Finder • Real-time Pet Notifier", icon_url="https://i.imgur.com/8Km9tLL.png")
    embed.set_thumbnail(url="https://i.imgur.com/8Km9tLL.png")  # Replace with your gold icon URL
    
    return embed

def create_status_embed(title: str, description: str, is_error: bool = False) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=DARK_GOLD if is_error else GOLD
    )
    embed.set_footer(text="Vexis Finder")
    return embed

def create_config_embed(channels: list) -> discord.Embed:
    channel_mentions = ", ".join([f"<#{ch}>" for ch in channels]) if channels else "No channels set"
    embed = discord.Embed(
        title="⚙️ Vexis Finder Configuration",
        description=f"**Configured Channels:**\n{channel_mentions}",
        color=GOLD
    )
    embed.add_field(name="📝 Usage", value="`/setch #channel1 #channel2 #channel3`\n`/reconnect`\n`/status`", inline=False)
    embed.set_footer(text="Vexis Finder • Black & Gold Edition")
    return embed
