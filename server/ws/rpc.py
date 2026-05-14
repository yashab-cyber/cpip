"""
RPC protocol handler for WebSocket.

Dispatches incoming RPC calls to registered handlers,
manages request/response correlation, and handles streaming.
"""

from __future__ import annotations

import asyncio
import time
import traceback
from typing import Any, Callable, Coroutine

from shared.protocol import (
    MessageType, RPCMessage, make_error, make_result,
    make_stream_chunk, make_stream_end, make_stream_start,
)


class RPCDispatcher:
    """Dispatches RPC method calls to registered handlers."""

    def __init__(self):
        self._handlers: dict[str, Callable] = {}

    def register(self, method: str, handler: Callable) -> None:
        self._handlers[method] = handler

    async def dispatch(self, msg: RPCMessage) -> RPCMessage:
        """Dispatch an RPC call and return the result message."""
        method = msg.method or ""
        handler = self._handlers.get(method)
        if not handler:
            return make_error(msg.id, "METHOD_NOT_FOUND", f"Unknown method: {method}")

        try:
            start = time.time()
            if asyncio.iscoroutinefunction(handler):
                result = await handler(msg.params)
            else:
                result = handler(msg.params)
            duration = (time.time() - start) * 1000

            response = make_result(msg.id, result)
            response.metadata["duration_ms"] = round(duration, 2)
            return response
        except Exception as e:
            return make_error(msg.id, "EXECUTION_ERROR", str(e), traceback.format_exc())


# Global dispatcher with built-in methods
dispatcher = RPCDispatcher()


# Register built-in RPC methods
async def _handle_ping(params: dict) -> dict:
    return {"pong": True, "timestamp": time.time()}

async def _handle_echo(params: dict) -> dict:
    return params

dispatcher.register("ping", _handle_ping)
dispatcher.register("echo", _handle_echo)
