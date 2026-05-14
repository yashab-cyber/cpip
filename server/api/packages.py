"""Package registry API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from server.auth.middleware import get_current_user
from server.auth.rate_limiter import DEFAULT_LIMIT, check_rate_limit
from server.services.package_service import package_service
from shared.models import PackageInfo

router = APIRouter(prefix="/api/v1/packages", tags=["packages"])


@router.get("/{name}", response_model=PackageInfo)
async def get_package(
    name: str,
    arch: str = Query("aarch64"),
    python: str = Query("3.11"),
    version: str = Query("latest"),
    request: Request = None,
):
    """Get package metadata and recommended strategy."""
    check_rate_limit(request, DEFAULT_LIMIT)
    info = await package_service.get_package(name, arch, python, version)
    if not info:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")
    return info


@router.get("/{name}/wheel")
async def get_wheel(
    name: str,
    arch: str = Query("aarch64"),
    python: str = Query("3.11"),
    request: Request = None,
):
    """Get download URL for prebuilt wheel."""
    check_rate_limit(request, DEFAULT_LIMIT)
    url = await package_service.get_wheel_url(name, arch, python)
    if not url:
        raise HTTPException(status_code=404, detail="No wheel available")
    return {"url": url, "package": name}


@router.get("/{name}/layers")
async def get_layers(name: str, request: Request = None):
    """Get package layer manifest for virtualization."""
    check_rate_limit(request, DEFAULT_LIMIT)
    layers = await package_service.get_layers(name)
    return {"package": name, "layers": layers}


@router.get("/")
async def search_packages(
    q: str = Query(""),
    arch: str = Query("aarch64"),
    limit: int = Query(50, le=100),
    request: Request = None,
):
    """Search available packages."""
    check_rate_limit(request, DEFAULT_LIMIT)
    results = await package_service.search(q, arch, limit)
    return {"packages": results, "total": len(results)}


@router.get("/catalog")
async def get_catalog(arch: str = Query("aarch64"), request: Request = None):
    """Get full package catalog for sync."""
    check_rate_limit(request, DEFAULT_LIMIT)
    packages = await package_service.get_catalog(arch)
    return {"packages": packages}
