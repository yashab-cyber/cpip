"""Container lifecycle and pool management."""

from __future__ import annotations

import asyncio
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Container:
    id: str
    name: str
    image: str
    status: str = "created"  # created, running, stopped
    gpu: bool = False


class ContainerPool:
    """Manages a pool of warm containers for fast execution."""

    def __init__(self, pool_size: int = 5):
        self.pool_size = pool_size
        self._available: list[Container] = []
        self._in_use: dict[str, Container] = {}

    async def acquire(self, image: str = "python:3.11-slim", gpu: bool = False) -> Container:
        # Try to find available container with matching image
        for i, c in enumerate(self._available):
            if c.image == image and c.gpu == gpu:
                container = self._available.pop(i)
                self._in_use[container.id] = container
                return container
        # Create new container
        container = await self._create(image, gpu)
        self._in_use[container.id] = container
        return container

    async def release(self, container_id: str) -> None:
        container = self._in_use.pop(container_id, None)
        if container and len(self._available) < self.pool_size:
            self._available.append(container)
        elif container:
            await self._destroy(container)

    async def _create(self, image: str, gpu: bool) -> Container:
        name = f"cpip-pool-{uuid.uuid4().hex[:8]}"
        return Container(id=name, name=name, image=image, status="running", gpu=gpu)

    async def _destroy(self, container: Container) -> None:
        await asyncio.to_thread(
            subprocess.run, ["docker", "rm", "-f", container.name], capture_output=True,
        )

    async def warmup(self) -> None:
        """Pre-start containers for common images."""
        images = ["python:3.11-slim"]
        for img in images[:self.pool_size]:
            c = await self._create(img, False)
            self._available.append(c)

    @property
    def stats(self) -> dict:
        return {"available": len(self._available), "in_use": len(self._in_use), "pool_size": self.pool_size}


container_pool = ContainerPool()
