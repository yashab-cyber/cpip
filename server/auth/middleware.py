"""
Authentication middleware for FastAPI.

Extracts and validates JWT tokens from requests.
Supports dev mode bypass for local development.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.auth.jwt_handler import decode_token
from server.config import server_config

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Extract and validate current user from JWT token."""
    # Dev mode bypass
    if server_config.debug:
        if credentials and credentials.credentials.startswith("dev_"):
            return {"sub": "dev-user", "device_id": credentials.credentials[4:], "tier": "dev"}
        if not credentials:
            return {"sub": "anonymous", "device_id": "local", "tier": "dev"}

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return payload


async def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """Dependency that requires valid authentication."""
    if user.get("sub") == "anonymous":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
