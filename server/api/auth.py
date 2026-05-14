"""Authentication API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.auth.jwt_handler import create_token_pair, decode_token
from server.auth.middleware import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    api_key: str = ""
    device_id: str = ""


class RegisterRequest(BaseModel):
    email: str | None = None


@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate and get JWT tokens."""
    device_id = req.device_id or str(uuid.uuid4())
    # In dev mode, accept any api_key
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    tokens = create_token_pair(user_id, device_id)
    tokens["device_id"] = device_id
    return tokens


@router.post("/register")
async def register(req: RegisterRequest):
    """Register a new user/device."""
    user_id = str(uuid.uuid4())
    api_key = f"cpip_{uuid.uuid4().hex}"
    device_id = str(uuid.uuid4())
    tokens = create_token_pair(user_id, device_id)
    return {**tokens, "user_id": user_id, "api_key": api_key, "device_id": device_id}


@router.post("/refresh")
async def refresh(refresh_token: str):
    """Refresh access token."""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    tokens = create_token_pair(payload["sub"], payload.get("device_id", ""))
    return tokens


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return {"user_id": user.get("sub"), "device_id": user.get("device_id"), "tier": user.get("tier", "free")}
