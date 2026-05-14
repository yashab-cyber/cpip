"""Server configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ServerConfig:
    host: str = os.getenv("CPIP_HOST", "0.0.0.0")
    port: int = int(os.getenv("CPIP_PORT", "8000"))
    debug: bool = os.getenv("CPIP_DEBUG", "false").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cpip.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    jwt_secret: str = os.getenv("JWT_SECRET", "cpip-dev-secret-change-in-production")
    cors_origins: list[str] = None  # type: ignore

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]

    @classmethod
    def from_env(cls) -> ServerConfig:
        return cls()


server_config = ServerConfig.from_env()
