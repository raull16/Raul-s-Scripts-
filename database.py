import sqlite3
import json
from typing import List, Dict

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
