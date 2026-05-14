"""
Background sync manager.

Periodically syncs package metadata and prefetches common packages
from the cloud registry. Runs as a background async task.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import httpx

from client.cache import CacheManager
from client.config import CpipConfig
from shared.constants import API_V1_PREFIX
from shared.platform import get_system_info


class SyncManager:
    """Manages background syncing of package metadata with cloud."""

    def __init__(self, config: CpipConfig, cache: CacheManager):
        self.config = config
        self.cache = cache
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_sync: float = 0
        self._sync_interval = 3600  # 1 hour

    async def start(self) -> None:
        """Start the background sync loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())

    async def stop(self) -> None:
        """Stop the background sync loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def sync_now(self) -> dict:
        """Trigger an immediate sync. Returns sync results."""
        return await self._do_sync()

    async def _sync_loop(self) -> None:
        """Background sync loop."""
        while self._running:
            try:
                if time.time() - self._last_sync >= self._sync_interval:
                    await self._do_sync()
            except Exception:
                pass
            await asyncio.sleep(60)

    async def _do_sync(self) -> dict:
        """Perform a full sync with cloud."""
        results: dict = {"metadata_updated": 0, "errors": [], "timestamp": time.time()}

        try:
            async with httpx.AsyncClient(
                base_url=self.config.cloud.api_url, timeout=30
            ) as client:
                # Sync device capabilities
                system = get_system_info()
                await client.post(
                    f"{API_V1_PREFIX}/devices/register",
                    json={
                        "device_id": self.config.auth.device_id,
                        "architecture": system.architecture,
                        "platform_tag": system.platform_tag,
                        "python_version": system.python_version,
                    },
                )

                # Fetch updated package catalog
                resp = await client.get(f"{API_V1_PREFIX}/packages/catalog", params={"arch": system.architecture})
                if resp.status_code == 200:
                    catalog = resp.json()
                    for pkg in catalog.get("packages", []):
                        self.cache.store_metadata(pkg["name"], pkg)
                        results["metadata_updated"] += 1

        except Exception as e:
            results["errors"].append(str(e))

        self._last_sync = time.time()
        # Save sync state
        sync_file = Path(self.config.home) / ".last_sync"
        sync_file.write_text(json.dumps(results, default=str), encoding="utf-8")
        return results

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_sync_time(self) -> float:
        return self._last_sync
