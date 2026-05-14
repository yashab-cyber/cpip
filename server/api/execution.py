"""Execution API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from server.auth.middleware import require_auth
from server.auth.rate_limiter import EXEC_LIMIT, check_rate_limit
from server.services.execution_service import execution_service
from shared.models import ExecutionRequest, ExecutionResult

router = APIRouter(prefix="/api/v1/execute", tags=["execution"])


@router.post("/", response_model=ExecutionResult)
async def submit_execution(
    req: ExecutionRequest,
    request: Request = None,
    user: dict = Depends(require_auth),
):
    """Submit code for remote execution."""
    check_rate_limit(request, EXEC_LIMIT)
    result = await execution_service.execute(req)
    return result


@router.get("/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution status and result."""
    result = await execution_service.get_result(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result


@router.delete("/{execution_id}")
async def cancel_execution(execution_id: str, user: dict = Depends(require_auth)):
    """Cancel a running execution."""
    await execution_service.cancel(execution_id)
    return {"status": "cancelled"}
