"""
Result streaming engine.

Handles streaming of large results from cloud execution back to client,
with backpressure, progress reporting, and reassembly.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable

from shared.protocol import MessageType, RPCMessage


class StreamReceiver:
    """Receives and reassembles streamed results from cloud."""

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.chunks: list[Any] = []
        self.metadata: dict[str, Any] = {}
        self.complete = False
        self._event = asyncio.Event()
        self._error: Exception | None = None

    def on_start(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata

    def on_chunk(self, data: Any, index: int) -> None:
        while len(self.chunks) <= index:
            self.chunks.append(None)
        self.chunks[index] = data

    def on_end(self) -> None:
        self.complete = True
        self._event.set()

    def on_error(self, error: Exception) -> None:
        self._error = error
        self._event.set()

    async def wait(self, timeout: float = 300) -> Any:
        """Wait for stream completion and return assembled result."""
        await asyncio.wait_for(self._event.wait(), timeout=timeout)
        if self._error:
            raise self._error
        return self._assemble()

    def _assemble(self) -> Any:
        """Assemble chunks into final result."""
        content_type = self.metadata.get("content_type", "json")
        if content_type == "bytes":
            return b"".join(c if isinstance(c, bytes) else str(c).encode() for c in self.chunks)
        if content_type == "text":
            return "".join(str(c) for c in self.chunks)
        if len(self.chunks) == 1:
            return self.chunks[0]
        return self.chunks


class StreamManager:
    """Manages multiple active streams."""

    def __init__(self):
        self._streams: dict[str, StreamReceiver] = {}

    def create_stream(self, call_id: str) -> StreamReceiver:
        receiver = StreamReceiver(call_id)
        self._streams[call_id] = receiver
        return receiver

    def handle_message(self, msg: RPCMessage) -> None:
        receiver = self._streams.get(msg.id)
        if not receiver:
            return
        if msg.type == MessageType.STREAM_START:
            receiver.on_start(msg.metadata)
        elif msg.type == MessageType.STREAM_CHUNK:
            receiver.on_chunk(msg.result, msg.metadata.get("index", 0))
        elif msg.type == MessageType.STREAM_END:
            receiver.on_end()
            del self._streams[msg.id]

    def get_stream(self, call_id: str) -> StreamReceiver | None:
        return self._streams.get(call_id)
