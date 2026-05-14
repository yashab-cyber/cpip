"""
Call interceptor and cloud execution session.

Manages the connection to the cloud execution engine, serializes
function calls, and deserializes results transparently.
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from typing import Any

from shared.protocol import MessageType, RPCMessage, make_call


class CloudSession:
    """
    Manages a cloud execution session for proxy modules.

    Handles RPC communication with the cloud execution engine
    via WebSocket, with sync/async support.
    """

    def __init__(self, config: Any = None):
        self.config = config
        self.session_id = str(uuid.uuid4())
        self._ws = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._connected = False
        self._lock = threading.Lock()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Ensure we have a running event loop in a background thread."""
        if self._loop is None or not self._loop.is_running():
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            # Wait for loop to start
            import time
            for _ in range(50):
                if self._loop.is_running():
                    break
                time.sleep(0.01)
        return self._loop

    def _run_loop(self) -> None:
        """Run the event loop in background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()  # type: ignore[union-attr]

    async def _connect(self) -> None:
        """Establish WebSocket connection to cloud."""
        if self._connected:
            return
        try:
            import websockets
            ws_url = "ws://localhost:8000/ws"
            if self.config:
                ws_url = getattr(getattr(self.config, "cloud", None), "ws_url", ws_url)

            self._ws = await websockets.connect(ws_url, max_size=64 * 1024 * 1024)
            self._connected = True

            # Start message receiver
            asyncio.ensure_future(self._receive_loop())
        except Exception:
            self._connected = False

    async def _receive_loop(self) -> None:
        """Receive and dispatch messages from cloud."""
        try:
            async for raw in self._ws:  # type: ignore[union-attr]
                try:
                    msg = RPCMessage.from_json(str(raw))
                    if msg.type == MessageType.RESULT:
                        future = self._pending.pop(msg.id, None)
                        if future and not future.done():
                            future.set_result(msg.result)
                    elif msg.type == MessageType.ERROR:
                        future = self._pending.pop(msg.id, None)
                        if future and not future.done():
                            error_msg = msg.error.get("message", "Remote error") if msg.error else "Remote error"
                            future.set_exception(RuntimeError(error_msg))
                except Exception:
                    continue
        except Exception:
            self._connected = False

    def execute(self, method: str, args: tuple, kwargs: dict) -> Any:
        """
        Execute a remote function call synchronously.

        Serializes arguments, sends via RPC, waits for result.
        """
        from runtime.serialization import serialize_args, deserialize_result

        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(
            self._async_execute(method, args, kwargs), loop
        )
        try:
            return future.result(timeout=300)
        except TimeoutError:
            raise TimeoutError(f"Cloud execution of {method} timed out")

    async def _async_execute(self, method: str, args: tuple, kwargs: dict) -> Any:
        """Execute a remote function call asynchronously."""
        await self._connect()

        from runtime.serialization import serialize_args, deserialize_result

        # Serialize arguments
        serialized_args = serialize_args(args)
        serialized_kwargs = serialize_args(kwargs) if kwargs else {}

        # Create RPC call
        msg = make_call("exec.call", {
            "session_id": self.session_id,
            "method": method,
            "args": serialized_args,
            "kwargs": serialized_kwargs,
        })

        # Setup response future
        response_future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[msg.id] = response_future

        # Send
        if self._ws:
            await self._ws.send(msg.to_json())

        # Wait for result
        result = await asyncio.wait_for(response_future, timeout=300)
        return deserialize_result(result)

    def get_module_dir(self, module_name: str) -> list[str]:
        """Get the directory listing of a remote module."""
        try:
            return self.execute(f"__dir__", (module_name,), {})
        except Exception:
            return []

    async def close(self) -> None:
        """Close the session."""
        if self._ws:
            await self._ws.close()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._connected = False
