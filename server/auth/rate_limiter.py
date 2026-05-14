"""
Rate limiter using in-memory storage (Redis-ready).

Implements sliding window rate limiting per client.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status


@dataclass
class RateLimit:
    requests: int
    window_seconds: int


class RateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        ip = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else "unknown"
        return f"rate:{ip}"

    def check(self, request: Request, limit: RateLimit) -> bool:
        key = self._client_key(request)
        now = time.time()
        window_start = now - limit.window_seconds

        # Clean old entries
        self._windows[key] = [t for t in self._windows[key] if t > window_start]

        if len(self._windows[key]) >= limit.requests:
            return False

        self._windows[key].append(now)
        return True

    def remaining(self, request: Request, limit: RateLimit) -> int:
        key = self._client_key(request)
        now = time.time()
        window_start = now - limit.window_seconds
        current = sum(1 for t in self._windows.get(key, []) if t > window_start)
        return max(0, limit.requests - current)


# Global instance
rate_limiter = RateLimiter()

# Default limits
DEFAULT_LIMIT = RateLimit(requests=100, window_seconds=60)
BUILD_LIMIT = RateLimit(requests=10, window_seconds=60)
EXEC_LIMIT = RateLimit(requests=50, window_seconds=60)


def check_rate_limit(request: Request, limit: RateLimit = DEFAULT_LIMIT) -> None:
    """Check rate limit and raise 429 if exceeded."""
    if not rate_limiter.check(request, limit):
        retry_after = limit.window_seconds
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after}s",
            headers={"Retry-After": str(retry_after)},
        )
