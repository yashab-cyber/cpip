"""
Proxy module factory.

Creates and manages proxy modules for cloud-executed packages,
with caching, submodule resolution, and attribute tracking.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

from runtime.hooks import ProxyModule


class ProxyFactory:
    """Factory for creating and managing proxy modules."""

    _instances: dict[str, ProxyModule] = {}

    @classmethod
    def create(cls, name: str, config: Any = None, pkg_info: dict | None = None) -> ProxyModule:
        """Create or get existing proxy module."""
        if name not in cls._instances:
            cls._instances[name] = ProxyModule(name, config, pkg_info)
        return cls._instances[name]

    @classmethod
    def get(cls, name: str) -> ProxyModule | None:
        return cls._instances.get(name)

    @classmethod
    def clear(cls) -> None:
        cls._instances.clear()

    @classmethod
    def list_proxies(cls) -> list[str]:
        return list(cls._instances.keys())
