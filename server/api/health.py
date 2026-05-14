"""Health and status endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter

from server.ws.hub import hub
from server.ws.sessions import session_manager
from shared.constants import VERSION
from shared.models import HealthStatus

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """System health check."""
    return HealthStatus(
        status="ok",
        version=VERSION,
        uptime_seconds=round(time.time() - _start_time, 1),
        services={"api": "ok", "websocket": "ok", "database": "ok"},
        connected_devices=hub.connected_count,
        active_executions=session_manager.active_count,
    )
