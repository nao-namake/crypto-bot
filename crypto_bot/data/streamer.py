"""crypto_bot.data.streamer module.

Provides RealTimeFetcher to receive real-time market data via WebSocket.
"""

import asyncio
import json
from typing import Any, Callable, Dict, Optional

import websockets


class RealTimeFetcher:
    """Fetch real-time ticks over WebSocket and provide them via callback or queue."""

    def __init__(
        self,
        url: str,
        symbol: str,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """
        Initialize the RealTimeFetcher.

        Args:
            url: WebSocket endpoint URL.
            symbol: Market symbol to subscribe (e.g. "BTCUSDT").
            on_message: Optional callback invoked for each parsed message.
        """
        self.url = url
        self.symbol = symbol
        self.on_message = on_message
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._task: Optional[asyncio.Task[Any]] = None
        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

    async def connect(self) -> None:
        """Connect to the WebSocket and send a subscription message."""
        self._ws = await websockets.connect(self.url)
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"trade.{self.symbol}"],
        }
        await self._ws.send(json.dumps(subscribe_msg))

    async def _recv_loop(self) -> None:
        """
        Receive messages from WebSocket, dispatch via callback, and enqueue.

        Loop until the connection is closed or the task is cancelled.
        """
        assert self._ws is not None, "Must call connect() before receiving."
        async for raw in self._ws:
            data = json.loads(raw)
            if self.on_message:
                self.on_message(data)
            await self._queue.put(data)

    def start(self) -> None:
        """Start the receive loop in the background as an asyncio Task."""
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run())

    async def _run(self) -> None:
        """Connect first, then enter the receive loop."""
        await self.connect()
        await self._recv_loop()

    async def stop(self) -> None:
        """Cancel receive task and close the WebSocket connection."""
        if self._task:
            self._task.cancel()
        if self._ws:
            await self._ws.close()

    async def get_message(self) -> Dict[str, Any]:
        """Get a message from the internal queue."""
        return await self._queue.get()
