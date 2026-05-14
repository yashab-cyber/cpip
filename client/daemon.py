"""
cpip background daemon.

Maintains persistent WebSocket connection to cloud, handles RPC requests
from import hooks, manages background syncing, and provides local services.
"""

from __future__ import annotations

import asyncio
import json
import signal
import time
from pathlib import Path

import websockets
from websockets.asyncio.client import connect as ws_connect

from client.cache import CacheManager
from client.config import CpipConfig, load_config
from client.sync import SyncManager
from shared.constants import WS_HEARTBEAT_INTERVAL, WS_RECONNECT_BASE_DELAY, WS_RECONNECT_MAX_DELAY
from shared.protocol import (
    MessageType, RPCMessage, make_heartbeat, make_heartbeat_ack, make_result, make_error,
)


class CpipDaemon:
    """Background daemon managing cloud connection and local services."""

    def __init__(self, config: CpipConfig | None = None):
        self.config = config or load_config()
        self.cache = CacheManager(self.config.cache.max_size_mb)
        self.sync = SyncManager(self.config, self.cache)
        self._ws = None
        self._running = False
        self._reconnect_delay = WS_RECONNECT_BASE_DELAY
        self._pending: dict[str, asyncio.Future] = {}
        self._pid_file = Path(self.config.home) / "daemon.pid"

    async def start(self) -> None:
        """Start the daemon."""
        self._running = True
        self._write_pid()

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # Start background tasks
        await self.sync.start()
        await self._connection_loop()

    async def stop(self) -> None:
        """Stop the daemon gracefully."""
        self._running = False
        await self.sync.stop()
        if self._ws:
            await self._ws.close()
        self._pid_file.unlink(missing_ok=True)

    async def _connection_loop(self) -> None:
        """Maintain persistent WebSocket connection with auto-reconnect."""
        while self._running:
            try:
                async with ws_connect(
                    self.config.cloud.ws_url,
                    extra_headers={"Authorization": f"Bearer {self.config.auth.token}"} if self.config.auth.token else {},
                    ping_interval=WS_HEARTBEAT_INTERVAL,
                    max_size=64 * 1024 * 1024,
                ) as ws:
                    self._ws = ws
                    self._reconnect_delay = WS_RECONNECT_BASE_DELAY

                    # Send session init
                    from shared.platform import get_system_info
                    from shared.protocol import make_session_init
                    info = get_system_info()
                    await ws.send(make_session_init(info.__dict__).to_json())  # type: ignore[arg-type]

                    # Message handling loop
                    async for raw in ws:
                        try:
                            msg = RPCMessage.from_json(str(raw))
                            await self._handle_message(msg)
                        except Exception:
                            continue

            except (websockets.exceptions.ConnectionClosed, OSError, Exception):
                if not self._running:
                    break
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, WS_RECONNECT_MAX_DELAY)

    async def _handle_message(self, msg: RPCMessage) -> None:
        """Handle incoming WebSocket message."""
        if msg.type == MessageType.HEARTBEAT:
            if self._ws:
                await self._ws.send(make_heartbeat_ack(msg.id).to_json())

        elif msg.type == MessageType.RESULT:
            future = self._pending.pop(msg.id, None)
            if future and not future.done():
                future.set_result(msg.result)

        elif msg.type == MessageType.ERROR:
            future = self._pending.pop(msg.id, None)
            if future and not future.done():
                future.set_exception(Exception(msg.error.get("message", "Unknown error") if msg.error else "Unknown"))

        elif msg.type == MessageType.CALL:
            # Handle server-initiated calls (e.g., cache invalidation)
            result = await self._dispatch(msg.method or "", msg.params)
            if self._ws:
                await self._ws.send(make_result(msg.id, result).to_json())

    async def _dispatch(self, method: str, params: dict) -> dict:
        """Dispatch server-initiated RPC calls."""
        handlers = {
            "cache.invalidate": self._handle_cache_invalidate,
            "sync.trigger": self._handle_sync_trigger,
            "status": self._handle_status,
        }
        handler = handlers.get(method)
        if handler:
            return await handler(params)
        return {"error": f"Unknown method: {method}"}

    async def _handle_cache_invalidate(self, params: dict) -> dict:
        package = params.get("package", "")
        if package:
            # Remove from metadata cache
            meta_path = Path(self.cache.metadata_dir) / f"{package}.json"
            meta_path.unlink(missing_ok=True)
        return {"status": "ok"}

    async def _handle_sync_trigger(self, _params: dict) -> dict:
        result = await self.sync.sync_now()
        return {"status": "ok", "updated": result.get("metadata_updated", 0)}

    async def _handle_status(self, _params: dict) -> dict:
        stats = self.cache.stats()
        return {
            "status": "running",
            "cache_size_mb": stats.total_size_mb,
            "sync_running": self.sync.is_running,
        }

    async def rpc_call(self, method: str, params: dict | None = None, timeout: float = 300) -> dict:
        """Send an RPC call to the cloud and wait for result."""
        if not self._ws:
            raise ConnectionError("Not connected to cloud")

        from shared.protocol import make_call
        msg = make_call(method, params)
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[msg.id] = future

        await self._ws.send(msg.to_json())
        return await asyncio.wait_for(future, timeout=timeout)

    def _write_pid(self) -> None:
        """Write PID file for daemon management."""
        import os
        self._pid_file.write_text(str(os.getpid()), encoding="utf-8")

    @staticmethod
    def is_running(config: CpipConfig | None = None) -> bool:
        """Check if daemon is already running."""
        import os
        cfg = config or load_config()
        pid_file = Path(cfg.home) / "daemon.pid"
        if not pid_file.exists():
            return False
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            pid_file.unlink(missing_ok=True)
            return False


def run_daemon() -> None:
    """Entry point for daemon process."""
    daemon = CpipDaemon()
    asyncio.run(daemon.start())
