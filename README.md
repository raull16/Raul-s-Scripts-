# Vexis Finder Discord Bot

A Discord bot that monitors the Vexis Finder WebSocket and sends real-time pet findings to configured channels via webhooks.

## Features

- 🔌 WebSocket connection to `wss://join.signorefinderws.org/ws`
- 📡 Real-time pet finding notifications
- 🎨 Black & Gold themed embeds
- 🔧 Slash commands for easy configuration
- 🕸️ Webhook-based delivery (no bot message limits)
- 🔄 Auto-reconnect with exponential backoff
- 💾 SQLite database for persistent configuration

## Commands

| Command | Description |
|---------|-------------|
| `/setch #ch1 #ch2 #ch3` | Configure up to 3 channels (creates webhooks) |
| `/removech` | Remove all configured channels |
| `/reconnect` | Force WebSocket reconnection |
| `/status` | Check bot and WebSocket status |
| `/test` | Send a test notification |

## Deployment on Railway

1. Create a new Railway project
2. Add your Discord Bot Token as `TOKEN` in Environment Variables
3. Deploy from GitHub repository
4. Invite the bot with `applications.commands` and `manage_webhooks` scopes

## Requirements

- Python 3.9+
- discord.py
- websockets
- aiohttp

## License

MIT
