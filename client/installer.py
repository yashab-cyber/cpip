"""
Unified package installer.

Routes installation through the correct strategy (local pip, Termux pkg,
cloud wheel download, cloud build request, or cloud execution proxy setup).
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import httpx

from client.cache import CacheManager
from client.config import CpipConfig
from client.resolver import PackageResolver
from client.ui.console import print_cloud, print_error, print_info, print_success, print_warning
from client.ui.progress import download_progress
from shared.constants import API_V1_PREFIX
from shared.exceptions import PackageInstallError
from shared.models import PackageResolution, PackageStrategy


class PackageInstaller:
    """Installs packages using the optimal strategy determined by the resolver."""

    def __init__(self, config: CpipConfig, cache: CacheManager, resolver: PackageResolver):
        self.config = config
        self.cache = cache
        self.resolver = resolver

    async def install(self, package: str, version: str = "latest", force: bool = False) -> bool:
        """Install a package using the best available strategy."""
        resolution = await self.resolver.resolve(package, version)

        if resolution.strategy == PackageStrategy.LOCAL_INSTALL and not force:
            if resolution.reason == "Already installed locally":
                print_info(f"{package} is already installed")
                return True

        strategies = [resolution.strategy] + resolution.fallback_strategies
        for strategy in strategies:
            try:
                success = await self._execute_strategy(package, version, strategy, resolution)
                if success:
                    return True
                print_warning(f"Strategy {strategy.value} failed, trying next...")
            except Exception as e:
                print_warning(f"Strategy {strategy.value} error: {e}")
                continue

        raise PackageInstallError(package, "All strategies exhausted")

    async def _execute_strategy(
        self, package: str, version: str, strategy: PackageStrategy, resolution: PackageResolution
    ) -> bool:
        """Execute a specific installation strategy."""
        handlers = {
            PackageStrategy.LOCAL_INSTALL: self._install_local,
            PackageStrategy.TERMUX_PKG: self._install_termux,
            PackageStrategy.CLOUD_WHEEL: self._install_cloud_wheel,
            PackageStrategy.CLOUD_BUILD: self._install_cloud_build,
            PackageStrategy.CLOUD_EXEC: self._setup_cloud_exec,
            PackageStrategy.HYBRID: self._setup_hybrid,
        }
        handler = handlers.get(strategy)
        if not handler:
            return False
        return await handler(package, version, resolution)

    async def _install_local(self, package: str, version: str, _res: PackageResolution) -> bool:
        """Standard pip install."""
        print_info(f"Installing {package} locally...")
        cached = self.cache.get_wheel(package, version)
        cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
        if cached:
            cmd.append(str(cached))
        elif version != "latest":
            cmd.append(f"{package}=={version}")
        else:
            cmd.append(package)

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            print_success(f"{package} installed locally")
            return True
        print_error(f"pip install failed: {stderr.decode('utf-8', errors='ignore')[:200]}")
        return False

    async def _install_termux(self, package: str, _version: str, _res: PackageResolution) -> bool:
        """Install via Termux pkg."""
        print_info(f"Installing {package} via Termux pkg...")
        cmd = ["pkg", "install", "-y", f"python-{package}"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode == 0:
            print_success(f"{package} installed via Termux")
            return True
        return False

    async def _install_cloud_wheel(self, package: str, version: str, res: PackageResolution) -> bool:
        """Download prebuilt wheel from cloud and install."""
        print_cloud(f"Downloading prebuilt wheel for {package}...")
        wheel_url = res.info.wheel_url if res.info else None
        if not wheel_url:
            wheel_url = await self._get_wheel_url(package, version)
        if not wheel_url:
            return False

        wheel_path = await self._download_wheel(package, wheel_url)
        if not wheel_path:
            return False

        self.cache.store_wheel(package, version, wheel_path, res.info.wheel_hash if res.info and res.info.wheel_hash else "")
        cmd = [sys.executable, "-m", "pip", "install", "--quiet", str(wheel_path)]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode == 0:
            print_success(f"{package} installed from cloud wheel")
            return True
        return False

    async def _install_cloud_build(self, package: str, version: str, _res: PackageResolution) -> bool:
        """Request cloud build and install resulting wheel."""
        print_cloud(f"Requesting cloud build for {package}...")
        try:
            async with httpx.AsyncClient(base_url=self.config.cloud.api_url, timeout=600) as client:
                resp = await client.post(
                    f"{API_V1_PREFIX}/builds/",
                    json={"package_name": package, "package_version": version, "target_architecture": "aarch64"},
                )
                if resp.status_code in (200, 201):
                    build_data = resp.json()
                    print_cloud(f"Build queued: {build_data.get('request_id', 'unknown')}")
                    # Poll for completion
                    build_id = build_data.get("request_id")
                    for _ in range(360):  # 30 min max
                        await asyncio.sleep(5)
                        status_resp = await client.get(f"{API_V1_PREFIX}/builds/{build_id}")
                        if status_resp.status_code == 200:
                            status = status_resp.json()
                            if status.get("status") == "succeeded":
                                wheel_url = status.get("wheel_url")
                                if wheel_url:
                                    wheel_path = await self._download_wheel(package, wheel_url)
                                    if wheel_path:
                                        self.cache.store_wheel(package, version, wheel_path)
                                        return await self._install_local(package, version, _res)
                            elif status.get("status") == "failed":
                                print_error(f"Cloud build failed: {status.get('error', 'unknown')}")
                                return False
        except Exception as e:
            print_error(f"Cloud build error: {e}")
        return False

    async def _setup_cloud_exec(self, package: str, _version: str, _res: PackageResolution) -> bool:
        """Setup cloud execution proxy for a package."""
        print_cloud(f"Setting up cloud execution proxy for {package}...")
        # Register the package for cloud execution in runtime hooks
        from runtime.hooks import register_cloud_package
        register_cloud_package(package, self.config)
        print_success(f"{package} configured for cloud execution")
        print_info(f"  import {package}  →  transparently proxied to cloud")
        return True

    async def _setup_hybrid(self, package: str, _version: str, _res: PackageResolution) -> bool:
        """Setup hybrid local+cloud execution."""
        print_cloud(f"Setting up hybrid execution for {package}...")
        from runtime.hooks import register_cloud_package
        register_cloud_package(package, self.config, hybrid=True)
        print_success(f"{package} configured for hybrid execution (local + cloud GPU)")
        return True

    async def _get_wheel_url(self, package: str, version: str) -> str | None:
        """Query cloud for wheel download URL."""
        try:
            async with httpx.AsyncClient(base_url=self.config.cloud.api_url, timeout=30) as client:
                from shared.platform import get_system_info
                info = get_system_info()
                resp = await client.get(
                    f"{API_V1_PREFIX}/packages/{package}/wheel",
                    params={"arch": info.architecture, "python": f"{sys.version_info.major}.{sys.version_info.minor}"},
                )
                if resp.status_code == 200:
                    return resp.json().get("url")
        except Exception:
            pass
        return None

    async def _download_wheel(self, package: str, url: str) -> Path | None:
        """Download a wheel file with progress."""
        try:
            filename = url.split("/")[-1].split("?")[0]
            dest = Path(self.config.wheels_dir) / filename

            async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
                async with client.stream("GET", url) as resp:
                    total = int(resp.headers.get("content-length", 0))
                    with download_progress() as progress:
                        task = progress.add_task("download", total=total, package=package)
                        with open(dest, "wb") as f:
                            async for chunk in resp.aiter_bytes(chunk_size=8192):
                                f.write(chunk)
                                progress.advance(task, len(chunk))
            return dest
        except Exception as e:
            print_error(f"Download failed: {e}")
            return None
