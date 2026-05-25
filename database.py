import sqlite3
import asyncio
from threading import Lock

class Database:
    def __init__(self):
        self.conn = None
        self.lock = Lock()
    
    async def init(self):
        # Run in executor to not block async
        await asyncio.get_event_loop().run_in_executor(None, self._init_sync)
    
    def _init_sync(self):
        self.conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        cursor = self.conn.cursor()
        
        # Create all tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS panels (
                guild_id INTEGER,
                channel_id INTEGER,
                panel_data TEXT,
                PRIMARY KEY (guild_id, channel_id)
            )
        ''')
        
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hwids (
                user_id INTEGER,
                hwid TEXT,
                PRIMARY KEY (user_id, hwid)
            )
        ''')
        
        self.conn.commit()
    
    async def execute(self, query, *args):
        def _execute():
            cursor = self.conn.cursor()
            # Convert asyncpg-style placeholders ($1, $2) to sqlite (?)
            sqlite_query = query.replace('$1', '?').replace('$2', '?').replace('$3', '?').replace('$4', '?').replace('$5', '?')
            cursor.execute(sqlite_query, args)
            self.conn.commit()
            return cursor
        
        return await asyncio.get_event_loop().run_in_executor(None, _execute)
    
    async def fetchrow(self, query, *args):
        def _fetchrow():
            cursor = self.conn.cursor()
            sqlite_query = query.replace('$1', '?').replace('$2', '?').replace('$3', '?').replace('$4', '?').replace('$5', '?')
            cursor.execute(sqlite_query, args)
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
        
        return await asyncio.get_event_loop().run_in_executor(None, _fetchrow)
    
    async def fetch(self, query, *args):
        def _fetch():
            cursor = self.conn.cursor()
            sqlite_query = query.replace('$1', '?').replace('$2', '?').replace('$3', '?').replace('$4', '?').replace('$5', '?')
            cursor.execute(sqlite_query, args)
            rows = cursor.fetchall()
            if rows:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            return []
        
        return await asyncio.get_event_loop().run_in_executor(None, _fetch)
    
    async def acquire(self):
        # For compatibility - returns self as a context manager
        return self
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
