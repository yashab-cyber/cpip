"""
Package service — business logic for package registry.

Provides package lookup, strategy resolution, and catalog management.
Backed by in-memory registry (upgradeable to database/S3).
"""

from __future__ import annotations

from typing import Any

from shared.constants import CLOUD_PREFERRED_PACKAGES
from shared.models import PackageInfo, PackageStrategy


# In-memory package registry (production: PostgreSQL + S3)
_REGISTRY: dict[str, PackageInfo] = {}

# Seed with known heavy packages and their strategies
_SEED_PACKAGES = {
    "torch": PackageInfo(
        name="torch", version="2.4.0", description="PyTorch deep learning framework",
        strategy=PackageStrategy.HYBRID, requires_gpu=True, cloud_only=False,
        supported_architectures=["aarch64", "x86_64"],
        dependencies=["numpy", "typing_extensions"],
    ),
    "tensorflow": PackageInfo(
        name="tensorflow", version="2.16.0", description="TensorFlow ML framework",
        strategy=PackageStrategy.CLOUD_EXEC, requires_gpu=True, cloud_only=True,
        supported_architectures=["x86_64"],
        dependencies=["numpy", "protobuf", "grpcio"],
    ),
    "opencv-python": PackageInfo(
        name="opencv-python", version="4.9.0", description="OpenCV computer vision library",
        strategy=PackageStrategy.CLOUD_WHEEL, requires_gpu=False,
        supported_architectures=["aarch64", "x86_64"],
        dependencies=["numpy"],
    ),
    "scipy": PackageInfo(
        name="scipy", version="1.13.0", description="Scientific computing library",
        strategy=PackageStrategy.CLOUD_WHEEL, requires_gpu=False,
        supported_architectures=["aarch64", "x86_64"],
        dependencies=["numpy"],
    ),
    "playwright": PackageInfo(
        name="playwright", version="1.44.0", description="Browser automation",
        strategy=PackageStrategy.CLOUD_EXEC, requires_gpu=False, cloud_only=True,
        supported_architectures=["x86_64"],
    ),
    "numpy": PackageInfo(
        name="numpy", version="1.26.4", description="Numerical computing",
        strategy=PackageStrategy.LOCAL_INSTALL, requires_gpu=False,
        supported_architectures=["aarch64", "x86_64"],
    ),
}

# Initialize registry
for name, info in _SEED_PACKAGES.items():
    _REGISTRY[name] = info


class PackageService:
    """Package registry business logic."""

    async def get_package(self, name: str, arch: str = "aarch64", python: str = "3.11", version: str = "latest") -> PackageInfo | None:
        info = _REGISTRY.get(name)
        if info:
            # Clone and adjust for architecture
            data = info.model_dump()
            if arch not in (info.supported_architectures or []):
                data["strategy"] = PackageStrategy.CLOUD_EXEC.value
            return PackageInfo(**data)
        # For unknown packages, suggest local install
        if name not in CLOUD_PREFERRED_PACKAGES:
            return PackageInfo(name=name, version="latest", strategy=PackageStrategy.LOCAL_INSTALL)
        return PackageInfo(name=name, version="latest", strategy=PackageStrategy.CLOUD_EXEC, cloud_only=True)

    async def get_wheel_url(self, name: str, arch: str, python: str) -> str | None:
        info = _REGISTRY.get(name)
        if info and info.wheel_url:
            return info.wheel_url
        return None

    async def get_layers(self, name: str) -> list[dict]:
        info = _REGISTRY.get(name)
        if info and info.layers:
            return [l.model_dump() for l in info.layers]
        return []

    async def search(self, query: str, arch: str = "aarch64", limit: int = 50) -> list[dict]:
        results = []
        for name, info in _REGISTRY.items():
            if query.lower() in name.lower() or not query:
                results.append({"name": name, "version": info.version, "strategy": info.strategy.value})
                if len(results) >= limit:
                    break
        return results

    async def get_catalog(self, arch: str = "aarch64") -> list[dict]:
        return [
            {"name": name, "version": info.version, "strategy": info.strategy.value}
            for name, info in _REGISTRY.items()
        ]


package_service = PackageService()
