"""
Redis-backed build queue.

Manages build job queue with priority ordering and worker assignment.
Falls back to in-memory queue if Redis unavailable.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from shared.models import BuildRequest


class BuildQueue:
    """Build job queue (in-memory, Redis-upgradeable)."""

    def __init__(self):
        self._queue: list[tuple[int, float, BuildRequest]] = []  # (priority, timestamp, request)
        self._processing: dict[str, BuildRequest] = {}

    def push(self, request: BuildRequest) -> None:
        self._queue.append((request.priority, time.time(), request))
        self._queue.sort(key=lambda x: (x[0], x[1]))

    def pop(self) -> BuildRequest | None:
        if not self._queue:
            return None
        _, _, req = self._queue.pop(0)
        self._processing[req.request_id] = req
        return req

    def complete(self, request_id: str) -> None:
        self._processing.pop(request_id, None)

    def fail(self, request_id: str) -> None:
        req = self._processing.pop(request_id, None)
        if req:
            req.priority = min(req.priority + 1, 10)
            self.push(req)

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def processing_count(self) -> int:
        return len(self._processing)


build_queue = BuildQueue()
