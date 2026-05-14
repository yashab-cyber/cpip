"""
Container-inspired package layer system.

Each package is decomposed into content-addressed compressed layers.
Layers are shared across packages and versions for deduplication.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shared.constants import LAYERS_DIR


@dataclass
class PackageLayer:
    """A single immutable, content-addressed package layer."""
    layer_id: str
    sha256: str
    size: int
    content_type: str  # python, native, data
    files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PackageManifest:
    """Manifest describing a virtual package's layer composition."""
    name: str
    version: str
    layers: list[PackageLayer] = field(default_factory=list)
    entry_point: str = ""
    python_requires: str = ""
    dependencies: list[str] = field(default_factory=list)


class LayerManager:
    """Manages package layers: create, cache, compose, and mount."""

    def __init__(self, layers_dir: str = LAYERS_DIR):
        self.layers_dir = Path(layers_dir)
        self.layers_dir.mkdir(parents=True, exist_ok=True)

    def has_layer(self, layer_id: str) -> bool:
        return (self.layers_dir / layer_id).exists()

    def get_layer_path(self, layer_id: str) -> Path | None:
        path = self.layers_dir / layer_id
        return path if path.exists() else None

    def store_layer(self, data: bytes, content_type: str = "python") -> PackageLayer:
        """Store raw layer data. Returns layer info with content-addressed ID."""
        sha = hashlib.sha256(data).hexdigest()
        layer_id = sha[:16]
        layer_path = self.layers_dir / layer_id

        if not layer_path.exists():
            layer_path.mkdir(parents=True)
            # Extract compressed tar
            with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tmp:
                tmp.write(data)
                tmp.flush()
                with tarfile.open(tmp.name, "r:gz") as tar:
                    tar.extractall(path=str(layer_path))

        files = [str(p.relative_to(layer_path)) for p in layer_path.rglob("*") if p.is_file()]
        return PackageLayer(
            layer_id=layer_id, sha256=sha, size=len(data),
            content_type=content_type, files=files,
        )

    def compose_layers(self, layers: list[PackageLayer]) -> Path:
        """Compose multiple layers into a unified package directory."""
        composed = self.layers_dir / "composed" / hashlib.sha256(
            ":".join(l.layer_id for l in layers).encode()
        ).hexdigest()[:16]

        if composed.exists():
            return composed

        composed.mkdir(parents=True)
        for layer in layers:
            src = self.layers_dir / layer.layer_id
            if src.exists():
                for item in src.rglob("*"):
                    if item.is_file():
                        dest = composed / item.relative_to(src)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(item), str(dest))
        return composed

    def cleanup_unused(self, active_layers: set[str]) -> int:
        """Remove layers not in the active set. Returns count removed."""
        removed = 0
        for path in self.layers_dir.iterdir():
            if path.name == "composed" or path.name in active_layers:
                continue
            if path.is_dir():
                shutil.rmtree(path)
                removed += 1
        return removed

    def total_size_mb(self) -> float:
        total = sum(f.stat().st_size for f in self.layers_dir.rglob("*") if f.is_file())
        return total / (1024 * 1024)
