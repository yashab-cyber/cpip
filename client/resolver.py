"""
Package resolution engine.

Determines the optimal strategy for providing a package:
local install, Termux pkg, cloud wheel, cloud build, cloud execution, or hybrid.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from typing import Any

import httpx

from client.cache import CacheManager
from client.config import CpipConfig
from shared.constants import API_V1_PREFIX, CLOUD_PREFERRED_PACKAGES
from shared.models import PackageInfo, PackageResolution, PackageStrategy
from shared.platform import get_system_info


class PackageResolver:
    """Resolves optimal install/execution strategy for a package."""

    def __init__(self, config: CpipConfig, cache: CacheManager):
        self.config = config
        self.cache = cache
        self.system = get_system_info()
        self._http: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.config.cloud.api_url,
                timeout=self.config.cloud.timeout,
                headers={"Authorization": f"Bearer {self.config.auth.token}"} if self.config.auth.token else {},
            )
        return self._http

    async def resolve(self, package: str, version: str = "latest") -> PackageResolution:
        """Resolve the optimal strategy for a package."""
        if self._is_installed(package):
            return PackageResolution(
                package=package, version=self._installed_version(package) or version,
                strategy=PackageStrategy.LOCAL_INSTALL, reason="Already installed locally",
            )

        if self.cache.get_wheel(package, version):
            return PackageResolution(
                package=package, version=version,
                strategy=PackageStrategy.LOCAL_INSTALL, reason="Found in local cache",
            )

        if not self.config.runtime.offline_mode:
            cloud_info = await self._query_cloud(package, version)
            if cloud_info:
                return self._cloud_resolution(package, version, cloud_info)

        if self.system.is_termux and self._has_termux_pkg(package):
            return PackageResolution(
                package=package, version=version,
                strategy=PackageStrategy.TERMUX_PKG, reason="Available as Termux package",
            )

        if package in CLOUD_PREFERRED_PACKAGES:
            return PackageResolution(
                package=package, version=version,
                strategy=PackageStrategy.CLOUD_EXEC,
                reason="Heavy package — cloud execution recommended",
                fallback_strategies=[PackageStrategy.CLOUD_BUILD],
            )

        return PackageResolution(
            package=package, version=version,
            strategy=PackageStrategy.LOCAL_INSTALL,
            reason="Attempting local install with cloud fallback",
            fallback_strategies=[PackageStrategy.CLOUD_WHEEL, PackageStrategy.CLOUD_BUILD, PackageStrategy.CLOUD_EXEC],
        )

    def _cloud_resolution(self, package: str, version: str, info: PackageInfo) -> PackageResolution:
        strategy = info.strategy
        if info.requires_gpu and not self.system.has_gpu and self.config.runtime.gpu_offload:
            strategy = PackageStrategy.HYBRID
        fallbacks = [s for s in [PackageStrategy.CLOUD_EXEC, PackageStrategy.CLOUD_BUILD] if s != strategy]
        return PackageResolution(
            package=package, version=info.version or version,
            strategy=strategy, info=info, fallback_strategies=fallbacks,
            reason=f"Cloud registry: {strategy.value}",
        )

    async def _query_cloud(self, package: str, version: str) -> PackageInfo | None:
        try:
            client = await self._get_client()
            params: dict[str, Any] = {"arch": self.system.architecture, "python": f"{sys.version_info.major}.{sys.version_info.minor}"}
            if version != "latest":
                params["version"] = version
            resp = await client.get(f"{API_V1_PREFIX}/packages/{package}", params=params)
            if resp.status_code == 200:
                return PackageInfo(**resp.json())
        except Exception:
            pass
        return None

    @staticmethod
    def _is_installed(package: str) -> bool:
        return importlib.util.find_spec(package.replace("-", "_").lower()) is not None

    @staticmethod
    def _installed_version(package: str) -> str | None:
        try:
            from importlib.metadata import version as get_ver
            return get_ver(package)
        except Exception:
            return None

    @staticmethod
    def _has_termux_pkg(package: str) -> bool:
        try:
            r = subprocess.run(["apt", "list", f"python-{package}"], capture_output=True, text=True, timeout=10)
            return f"python-{package}" in r.stdout
        except Exception:
            return False

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()
