import asyncio
import json
import websockets
import aiohttp
from typing import Optional, Callable, Awaitable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketHandler:
    def __init__(self, url: str, on_message_callback: Callable[[dict], Awaitable[None]]):
        self.url = url
        self.on_message = on_message_callback
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._reconnect_delay = 5
        
    async def connect(self):
        """Connect to WebSocket and start listening"""
        self._running = True
        self._task = asyncio.create_task(self._run())
        return self
    
    async def _run(self):
        while self._running:
            try:
                logger.info(f"Connecting to WebSocket: {self.url}")
                async with websockets.connect(self.url, ping_interval=30, ping_timeout=10) as ws:
                    self.websocket = ws
                    logger.info("WebSocket connected successfully!")
                    self._reconnect_delay = 5
                    
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            logger.debug(f"Received: {data}")
                            await self.on_message(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON: {message}")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            
            if self._running:
                logger.info(f"Reconnecting in {self._reconnect_delay} seconds...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)
    
    async def reconnect(self):
        """Force reconnection"""
        logger.info("Manual reconnect requested")
        if self.websocket:
            await self.websocket.close()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = asyncio.create_task(self._run())
    
    async def disconnect(self):
        """Stop the WebSocket connection"""
        self._running = False
        if self.websocket:
            await self.websocket.close()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
