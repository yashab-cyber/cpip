"""Build API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from server.auth.middleware import require_auth
from server.auth.rate_limiter import BUILD_LIMIT, check_rate_limit
from server.services.build_service import build_service
from shared.models import BuildRequest, BuildResult

router = APIRouter(prefix="/api/v1/builds", tags=["builds"])


@router.post("/", response_model=BuildResult, status_code=201)
async def create_build(
    req: BuildRequest,
    request: Request = None,
    user: dict = Depends(require_auth),
):
    """Submit a new build request."""
    check_rate_limit(request, BUILD_LIMIT)
    result = await build_service.submit_build(req)
    return result


@router.get("/{build_id}", response_model=BuildResult)
async def get_build(build_id: str):
    """Get build status."""
    result = await build_service.get_build(build_id)
    if not result:
        raise HTTPException(status_code=404, detail="Build not found")
    return result


@router.get("/")
async def list_builds(limit: int = 20):
    """List recent builds."""
    builds = await build_service.list_builds(limit)
    return {"builds": builds}


@router.delete("/{build_id}")
async def cancel_build(build_id: str, user: dict = Depends(require_auth)):
    """Cancel a build."""
    success = await build_service.cancel_build(build_id)
    if not success:
        raise HTTPException(status_code=404, detail="Build not found or already completed")
    return {"status": "cancelled"}
