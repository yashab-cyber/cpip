"""
Build service — manages cloud build jobs.

Handles build submission, status tracking, and result retrieval.
Uses in-memory queue (upgradeable to Redis/Celery).
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from shared.models import BuildRequest, BuildResult, BuildStatus


class BuildService:
    """Build job management."""

    def __init__(self):
        self._builds: dict[str, BuildResult] = {}
        self._queue: list[str] = []

    async def submit_build(self, req: BuildRequest) -> BuildResult:
        result = BuildResult(
            request_id=req.request_id,
            status=BuildStatus.QUEUED,
            package_name=req.package_name,
            package_version=req.package_version,
        )
        self._builds[req.request_id] = result
        self._queue.append(req.request_id)
        return result

    async def get_build(self, build_id: str) -> BuildResult | None:
        return self._builds.get(build_id)

    async def list_builds(self, limit: int = 20) -> list[dict]:
        builds = list(self._builds.values())[-limit:]
        return [b.model_dump() for b in builds]

    async def cancel_build(self, build_id: str) -> bool:
        build = self._builds.get(build_id)
        if not build or build.status in (BuildStatus.SUCCEEDED, BuildStatus.FAILED):
            return False
        build.status = BuildStatus.CANCELLED
        if build_id in self._queue:
            self._queue.remove(build_id)
        return True

    @property
    def queue_size(self) -> int:
        return len(self._queue)


build_service = BuildService()
