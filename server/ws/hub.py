"""
WebSocket connection hub.

Manages active device connections, message routing,
heartbeat monitoring, and session lifecycle.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from shared.protocol import (
    MessageType, RPCMessage, make_heartbeat, make_result, make_error,
)


@dataclass
class DeviceConnection:
    device_id: str
    websocket: WebSocket
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class ConnectionHub:
    """Manages all WebSocket connections from devices."""

    def __init__(self):
        self._connections: dict[str, DeviceConnection] = {}
        self._lock = asyncio.Lock()

    async def connect(self, device_id: str, websocket: WebSocket, metadata: dict | None = None) -> DeviceConnection:
        await websocket.accept()
        conn = DeviceConnection(device_id=device_id, websocket=websocket, metadata=metadata or {})
        async with self._lock:
            # Close existing connection for this device
            if device_id in self._connections:
                try:
                    await self._connections[device_id].websocket.close()
                except Exception:
                    pass
            self._connections[device_id] = conn
        return conn

    async def disconnect(self, device_id: str) -> None:
        async with self._lock:
            conn = self._connections.pop(device_id, None)
            if conn:
                try:
                    await conn.websocket.close()
                except Exception:
                    pass

    async def send_to_device(self, device_id: str, message: RPCMessage) -> bool:
        conn = self._connections.get(device_id)
        if not conn:
            return False
        try:
            await conn.websocket.send_text(message.to_json())
            return True
        except Exception:
            await self.disconnect(device_id)
            return False

    async def broadcast(self, message: RPCMessage) -> int:
        sent = 0
        for device_id in list(self._connections.keys()):
            if await self.send_to_device(device_id, message):
                sent += 1
        return sent

    def get_connection(self, device_id: str) -> DeviceConnection | None:
        return self._connections.get(device_id)

    @property
    def connected_count(self) -> int:
        return len(self._connections)

    def list_devices(self) -> list[str]:
        return list(self._connections.keys())

    async def heartbeat_loop(self, interval: int = 30) -> None:
        """Send periodic heartbeats and clean dead connections."""
        while True:
            await asyncio.sleep(interval)
            now = time.time()
            for device_id in list(self._connections.keys()):
                conn = self._connections.get(device_id)
                if conn and now - conn.last_heartbeat > interval * 3:
                    await self.disconnect(device_id)
                elif conn:
                    try:
                        await conn.websocket.send_text(make_heartbeat().to_json())
                    except Exception:
                        await self.disconnect(device_id)


# Global hub instance
hub = ConnectionHub()
