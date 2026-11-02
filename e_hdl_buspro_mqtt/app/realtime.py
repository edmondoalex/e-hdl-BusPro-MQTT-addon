from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

from fastapi import WebSocket

_LOGGER = logging.getLogger("realtime")


@dataclass
class RealtimeEvent:
    type: str
    data: dict[str, Any]


class RealtimeHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        evt = {"type": event_type, "data": data}
        msg = json.dumps(evt, ensure_ascii=False)
        async with self._lock:
            clients = list(self._clients)
        if not clients:
            return

        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)

    async def close_all(self) -> None:
        async with self._lock:
            clients = list(self._clients)
            self._clients.clear()
        for ws in clients:
            try:
                await ws.close()
            except Exception:
                pass