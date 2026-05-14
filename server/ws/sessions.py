"""
WebSocket session management.

Tracks active execution sessions per device.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionSession:
    session_id: str
    device_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    active_modules: list[str] = field(default_factory=list)
    execution_count: int = 0


class SessionManager:
    """Manages execution sessions for connected devices."""

    def __init__(self):
        self._sessions: dict[str, ExecutionSession] = {}

    def create(self, session_id: str, device_id: str) -> ExecutionSession:
        session = ExecutionSession(session_id=session_id, device_id=device_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> ExecutionSession | None:
        return self._sessions.get(session_id)

    def get_by_device(self, device_id: str) -> list[ExecutionSession]:
        return [s for s in self._sessions.values() if s.device_id == device_id]

    def update_activity(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.last_active = time.time()
            session.execution_count += 1

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def cleanup_stale(self, max_idle_seconds: int = 3600) -> int:
        now = time.time()
        stale = [sid for sid, s in self._sessions.items() if now - s.last_active > max_idle_seconds]
        for sid in stale:
            del self._sessions[sid]
        return len(stale)

    @property
    def active_count(self) -> int:
        return len(self._sessions)


session_manager = SessionManager()
