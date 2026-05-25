import asyncpg
import json
import os

class Database:
    def __init__(self):
        self.pool = None
    
    async def init(self):
        # Use PostgreSQL (Railway provides this) or fallback to JSON
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            self.pool = await asyncpg.create_pool(database_url)
            await self.create_tables()
        else:
            self.use_json = True
            self.load_json_data()
    
    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS panels (
                    guild_id BIGINT,
                    channel_id BIGINT,
                    panel_data JSONB,
                    PRIMARY KEY (guild_id, channel_id)
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS keys (
                    key TEXT PRIMARY KEY,
                    panel_guild_id BIGINT,
                    panel_channel_id BIGINT,
                    time_limit INT,
                    used BOOLEAN DEFAULT FALSE,
                    used_by BIGINT DEFAULT NULL
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    user_id BIGINT PRIMARY KEY
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS whitelist (
                    user_id BIGINT PRIMARY KEY
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS buyer_roles (
                    guild_id BIGINT PRIMARY KEY,
                    role_id BIGINT
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS hwids (
                    user_id BIGINT,
                    hwid TEXT,
                    PRIMARY KEY (user_id, hwid)
                )
            ''')
