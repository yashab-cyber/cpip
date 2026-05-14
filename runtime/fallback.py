"""
Fallback and retry logic for cloud execution.

Implements retry with exponential backoff, strategy fallback chains,
and offline degradation for cloud operations.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

T = TypeVar("T")


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    retryable_exceptions: tuple = (ConnectionError, TimeoutError, OSError)


@dataclass
class FallbackChain:
    """Ordered list of strategies to try."""
    strategies: list[Callable] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    def add(self, strategy: Callable, label: str = "") -> FallbackChain:
        self.strategies.append(strategy)
        self.labels.append(label or f"strategy_{len(self.strategies)}")
        return self

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Try each strategy in order until one succeeds."""
        last_error = None
        for i, strategy in enumerate(self.strategies):
            try:
                if asyncio.iscoroutinefunction(strategy):
                    return await strategy(*args, **kwargs)
                return strategy(*args, **kwargs)
            except Exception as e:
                last_error = e
                continue
        raise last_error or RuntimeError("All strategies exhausted")


async def retry_async(
    func: Callable,
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> Any:
    """Retry an async function with exponential backoff."""
    cfg = config or RetryConfig()
    delay = cfg.base_delay
    last_error = None

    for attempt in range(cfg.max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except cfg.retryable_exceptions as e:
            last_error = e
            if attempt < cfg.max_retries:
                await asyncio.sleep(delay)
                delay = min(delay * cfg.backoff_factor, cfg.max_delay)
            continue

    raise last_error or RuntimeError("Retry exhausted")


class CircuitBreaker:
    """Circuit breaker pattern for cloud services."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._last_failure = 0.0
        self._state = "closed"  # closed, open, half-open

    @property
    def is_open(self) -> bool:
        if self._state == "open":
            if time.time() - self._last_failure > self.reset_timeout:
                self._state = "half-open"
                return False
            return True
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure = time.time()
        if self._failures >= self.failure_threshold:
            self._state = "open"

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        if self.is_open:
            raise ConnectionError("Circuit breaker is open — cloud unavailable")
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
