import os

TOKEN = os.environ.get("TOKEN")
WEBSOCKET_URL = "wss://join.signorefinderws.org/ws"

if not TOKEN:
    raise ValueError("TOKEN environment variable not set")
