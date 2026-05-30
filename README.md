# Vexis Finder Discord Bot

A Discord bot that monitors the Vexis Finder WebSocket and sends real-time pet findings to configured channels via webhooks.

## Commands

| Command | Description |
|---------|-------------|
| `/setch #ch1 #ch2 #ch3` | Configure up to 3 channels |
| `/removech` | Remove all configured channels |
| `/reconnect` | Force WebSocket reconnection |
| `/status` | Check bot and WebSocket status |
| `/test` | Send a test notification |

## Setup

1. Invite bot with `applications.commands` and `manage_webhooks` permissions
2. Use `/setch #channel` to configure
3. Bot will automatically send findings to configured channels

## Environment Variables

- `TOKEN` - Your Discord Bot Token
