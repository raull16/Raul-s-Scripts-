import sqlite3
import os
import json

class Database:
    def __init__(self):
        self.conn = None
        self.use_json = False
    
    async def init(self):
        # Use SQLite (no external database needed)
        self.conn = sqlite3.connect('bot_data.db')
        self.cursor = self.conn.cursor()
        await self.create_tables()
    
    async def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS panels (
                guild_id INTEGER,
                channel_id INTEGER,
                panel_data TEXT,
                PRIMARY KEY (guild_id, channel_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS keys (
                key TEXT PRIMARY KEY,
                panel_guild_id INTEGER,
                panel_channel_id INTEGER,
                time_limit INTEGER,
                used INTEGER DEFAULT 0,
                used_by INTEGER DEFAULT NULL
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS buyer_roles (
                guild_id INTEGER PRIMARY KEY,
                role_id INTEGER
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS hwids (
                user_id INTEGER,
                hwid TEXT,
                PRIMARY KEY (user_id, hwid)
            )
        ''')
        
        self.conn.commit()
    
    async def execute(self, query, *args):
        # Convert asyncpg style to sqlite
        if 'INSERT INTO' in query and 'ON CONFLICT' in query:
            # Handle ON CONFLICT for sqlite
            query = query.replace('ON CONFLICT', 'ON CONFLICT')
        
        self.cursor.execute(query, args)
        self.conn.commit()
    
    async def fetchrow(self, query, *args):
        self.cursor.execute(query, args)
        row = self.cursor.fetchone()
        if row:
            return dict(zip([desc[0] for desc in self.cursor.description], row))
        return None
    
    async def fetch(self, query, *args):
        self.cursor.execute(query, args)
        rows = self.cursor.fetchall()
        return [dict(zip([desc[0] for desc in self.cursor.description], row)) for row in rows]
    
    async def acquire(self):
        # For compatibility with asyncpg context manager
        class FakeConnection:
            def __init__(self, db):
                self.db = db
            
            async def execute(self, query, *args):
                self.db.cursor.execute(query, args)
                self.db.conn.commit()
            
            async def fetchrow(self, query, *args):
                self.db.cursor.execute(query, args)
                row = self.db.cursor.fetchone()
                if row:
                    return dict(zip([desc[0] for desc in self.db.cursor.description], row))
                return None
            
            async def fetch(self, query, *args):
                self.db.cursor.execute(query, args)
                rows = self.db.cursor.fetchall()
                return [dict(zip([desc[0] for desc in self.db.cursor.description], row)) for row in rows]
        
        return FakeConnection(self)
