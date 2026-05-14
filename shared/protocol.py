"""
WebSocket RPC wire protocol.

Defines message types, serialization format, and helper functions
for bidirectional JSON-RPC 2.0 communication over WebSocket.
"""

from __future__ import annotations

import json
import time
import uuid
from enum import Enum
from typing import Any

try:
    import msgpack

    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False


# ── Message Types ────────────────────────────────────────────────────

class MessageType(str, Enum):
    """RPC message types."""
    # Standard JSON-RPC 2.0
    CALL = "rpc.call"
    RESULT = "rpc.result"
    ERROR = "rpc.error"

    # Extensions for streaming and control
    STREAM_START = "rpc.stream.start"
    STREAM_CHUNK = "rpc.stream.chunk"
    STREAM_END = "rpc.stream.end"

    # Connection management
    HEARTBEAT = "rpc.heartbeat"
    HEARTBEAT_ACK = "rpc.heartbeat.ack"

    # Session
    SESSION_INIT = "session.init"
    SESSION_ACK = "session.ack"
    SESSION_END = "session.end"

    # Notifications (no response expected)
    NOTIFY = "rpc.notify"
    LOG = "rpc.log"
    PROGRESS = "rpc.progress"


# ── Message Structure ────────────────────────────────────────────────

class RPCMessage:
    """
    JSON-RPC 2.0-inspired message with cpip extensions.

    Format:
    {
        "jsonrpc": "2.0",
        "type": "rpc.call",
        "id": "uuid",
        "method": "package.install",
        "params": {...},
        "timestamp": 1234567890.123
    }
    """

    __slots__ = ("type", "id", "method", "params", "result", "error", "timestamp", "metadata")

    def __init__(
        self,
        type: MessageType,
        method: str | None = None,
        params: dict[str, Any] | None = None,
        result: Any = None,
        error: dict[str, Any] | None = None,
        id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.type = type
        self.id = id or str(uuid.uuid4())
        self.method = method
        self.params = params or {}
        self.result = result
        self.error = error
        self.timestamp = time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        msg: dict[str, Any] = {
            "jsonrpc": "2.0",
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "id": self.id,
            "timestamp": self.timestamp,
        }
        if self.method:
            msg["method"] = self.method
        if self.params:
            msg["params"] = self.params
        if self.result is not None:
            msg["result"] = self.result
        if self.error:
            msg["error"] = self.error
        if self.metadata:
            msg["metadata"] = self.metadata
        return msg

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    def to_bytes(self) -> bytes:
        """Serialize to msgpack bytes (fallback to JSON)."""
        if HAS_MSGPACK:
            return msgpack.packb(self.to_dict(), default=str)
        return self.to_json().encode("utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RPCMessage:
        """Deserialize from dictionary."""
        return cls(
            type=MessageType(data.get("type", "rpc.call")),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata"),
        )

    @classmethod
    def from_json(cls, raw: str) -> RPCMessage:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(raw))

    @classmethod
    def from_bytes(cls, raw: bytes) -> RPCMessage:
        """Deserialize from msgpack bytes (fallback to JSON)."""
        if HAS_MSGPACK:
            try:
                data = msgpack.unpackb(raw, raw=False)
                return cls.from_dict(data)
            except Exception:
                pass
        return cls.from_json(raw.decode("utf-8"))

    def __repr__(self) -> str:
        return f"RPCMessage(type={self.type.value}, id={self.id[:8]}..., method={self.method})"


# ── Helper Constructors ──────────────────────────────────────────────

def make_call(method: str, params: dict[str, Any] | None = None, **kwargs: Any) -> RPCMessage:
    """Create an RPC call message."""
    return RPCMessage(
        type=MessageType.CALL,
        method=method,
        params=params or kwargs,
    )


def make_result(call_id: str, result: Any) -> RPCMessage:
    """Create an RPC result message in response to a call."""
    return RPCMessage(
        type=MessageType.RESULT,
        id=call_id,
        result=result,
    )


def make_error(call_id: str, code: str, message: str, data: Any = None) -> RPCMessage:
    """Create an RPC error message in response to a call."""
    return RPCMessage(
        type=MessageType.ERROR,
        id=call_id,
        error={
            "code": code,
            "message": message,
            "data": data,
        },
    )


def make_heartbeat() -> RPCMessage:
    """Create a heartbeat ping message."""
    return RPCMessage(type=MessageType.HEARTBEAT)


def make_heartbeat_ack(ping_id: str) -> RPCMessage:
    """Create a heartbeat pong/ack message."""
    return RPCMessage(type=MessageType.HEARTBEAT_ACK, id=ping_id)


def make_stream_start(call_id: str, metadata: dict[str, Any] | None = None) -> RPCMessage:
    """Signal the start of a streaming response."""
    return RPCMessage(
        type=MessageType.STREAM_START,
        id=call_id,
        metadata=metadata,
    )


def make_stream_chunk(call_id: str, data: Any, index: int = 0) -> RPCMessage:
    """Send a chunk of streaming data."""
    return RPCMessage(
        type=MessageType.STREAM_CHUNK,
        id=call_id,
        result=data,
        metadata={"index": index},
    )


def make_stream_end(call_id: str) -> RPCMessage:
    """Signal the end of a streaming response."""
    return RPCMessage(type=MessageType.STREAM_END, id=call_id)


def make_notification(method: str, params: dict[str, Any] | None = None) -> RPCMessage:
    """Create a notification (no response expected)."""
    return RPCMessage(
        type=MessageType.NOTIFY,
        method=method,
        params=params,
    )


def make_log(level: str, message: str, source: str = "") -> RPCMessage:
    """Create a log message."""
    return RPCMessage(
        type=MessageType.LOG,
        params={"level": level, "message": message, "source": source},
    )


def make_progress(
    task: str, current: int, total: int, message: str = ""
) -> RPCMessage:
    """Create a progress update message."""
    return RPCMessage(
        type=MessageType.PROGRESS,
        params={
            "task": task,
            "current": current,
            "total": total,
            "message": message,
            "percent": round(current / max(total, 1) * 100, 1),
        },
    )


def make_session_init(device_info: dict[str, Any]) -> RPCMessage:
    """Create a session initialization message."""
    return RPCMessage(
        type=MessageType.SESSION_INIT,
        params=device_info,
    )
