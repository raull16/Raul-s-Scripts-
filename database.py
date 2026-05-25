import sqlite3
import asyncio
import os

class Database:
    def __init__(self):
        self.conn = None
    
    async def init(self):
        # Run in executor to not block async
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_sync)
    
    def _init_sync(self):
        self.conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        cursor = self.conn.cursor()
        
        # Create all tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keys (
                key TEXT PRIMARY KEY,
                panel_guild_id INTEGER,
                panel_channel_id INTEGER,
                time_limit INTEGER,
                used INTEGER DEFAULT 0,
                used_by INTEGER DEFAULT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buyer_roles (
                guild_id INTEGER PRIMARY KEY,
                role_id INTEGER
            )
        ''')
        
        self.conn.commit()
    
    def execute(self, query, *args):
        cursor = self.conn.cursor()
        # Convert $1, $2 to ?
        for i in range(1, 10):
            query = query.replace(f'${i}', '?')
        cursor.execute(query, args)
        self.conn.commit()
        return cursor
    
    def fetchrow(self, query, *args):
        cursor = self.conn.cursor()
        for i in range(1, 10):
            query = query.replace(f'${i}', '?')
        cursor.execute(query, args)
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def fetch(self, query, *args):
        cursor = self.conn.cursor()
        for i in range(1, 10):
            query = query.replace(f'${i}', '?')
        cursor.execute(query, args)
        rows = cursor.fetchall()
        if rows:
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []
