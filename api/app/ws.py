"""WebSocket hub for DVAP API (CONTRACTS.md §10).

Tracks active WS connections and broadcasts JSON envelopes:
  {"type": "scan_update", "scan": <Scan>}
  {"type": "beacon", "beacon": <Beacon>}
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WSHub:
    """Async-safe WebSocket connection manager."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.debug("WS client connected; total=%d", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            with contextlib.suppress(ValueError):
                self._connections.remove(ws)
        logger.debug("WS client disconnected; total=%d", len(self._connections))

    async def broadcast(self, payload: dict[str, object]) -> None:
        """Send payload to all active connections, dropping dead ones."""
        async with self._lock:
            live: list[WebSocket] = []
            for ws in self._connections:
                try:
                    await ws.send_json(payload)
                    live.append(ws)
                except Exception:
                    logger.debug("Dropping dead WS connection")
            self._connections = live


# Module-level singleton
hub = WSHub()
