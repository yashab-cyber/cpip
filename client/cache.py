"""
Local package cache manager.

Manages cached wheels, package layers, and metadata with LRU eviction,
integrity verification, and size-bounded storage.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from shared.constants import LAYERS_DIR, METADATA_DIR, WHEELS_DIR


@dataclass
class CacheEntry:
    """A cached item with metadata."""
    path: str
    package: str
    version: str
    sha256: str
    size: int
    cached_at: float
    last_accessed: float
    entry_type: str  # wheel, layer, metadata


@dataclass
class CacheStats:
    """Cache usage statistics."""
    total_size_mb: float
    max_size_mb: float
    num_wheels: int
    num_layers: int
    num_metadata: int
    utilization_pct: float


class CacheManager:
    """
    Manages the local cpip cache.

    Directory structure:
        ~/.cpip/cache/
        ├── wheels/       # Downloaded .whl files
        ├── layers/       # Virtual package layers
        ├── metadata/     # Package metadata JSON
        └── cache.json    # Cache index
    """

    def __init__(self, max_size_mb: int = 2048):
        self.max_size_mb = max_size_mb
        self.wheels_dir = Path(WHEELS_DIR)
        self.layers_dir = Path(LAYERS_DIR)
        self.metadata_dir = Path(METADATA_DIR)
        self._index_file = Path(WHEELS_DIR).parent / "cache.json"
        self._index: dict[str, dict] = {}

        # Ensure directories exist
        for d in (self.wheels_dir, self.layers_dir, self.metadata_dir):
            d.mkdir(parents=True, exist_ok=True)

        self._load_index()

    def _load_index(self) -> None:
        """Load cache index from disk."""
        if self._index_file.exists():
            try:
                self._index = json.loads(self._index_file.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                self._index = {}

    def _save_index(self) -> None:
        """Persist cache index to disk."""
        try:
            self._index_file.write_text(
                json.dumps(self._index, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    @staticmethod
    def _hash_file(path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _cache_key(self, package: str, version: str, entry_type: str) -> str:
        """Generate a unique cache key."""
        return f"{entry_type}:{package}:{version}"

    # ── Wheel Cache ──────────────────────────────────────────────────

    def get_wheel(self, package: str, version: str) -> Path | None:
        """Get cached wheel path if it exists and is valid."""
        key = self._cache_key(package, version, "wheel")
        entry = self._index.get(key)
        if not entry:
            return None

        path = Path(entry["path"])
        if not path.exists():
            del self._index[key]
            self._save_index()
            return None

        # Verify integrity
        if self._hash_file(path) != entry["sha256"]:
            path.unlink(missing_ok=True)
            del self._index[key]
            self._save_index()
            return None

        # Update access time
        entry["last_accessed"] = time.time()
        self._save_index()
        return path

    def store_wheel(self, package: str, version: str, source_path: Path, sha256: str = "") -> Path:
        """Store a wheel file in the cache."""
        self._maybe_evict()

        filename = source_path.name
        dest = self.wheels_dir / filename

        if source_path != dest:
            shutil.copy2(str(source_path), str(dest))

        actual_hash = sha256 or self._hash_file(dest)
        key = self._cache_key(package, version, "wheel")
        self._index[key] = {
            "path": str(dest),
            "package": package,
            "version": version,
            "sha256": actual_hash,
            "size": dest.stat().st_size,
            "cached_at": time.time(),
            "last_accessed": time.time(),
            "type": "wheel",
        }
        self._save_index()
        return dest

    # ── Layer Cache ──────────────────────────────────────────────────

    def get_layer(self, layer_id: str) -> Path | None:
        """Get cached layer directory if it exists."""
        key = f"layer:{layer_id}"
        entry = self._index.get(key)
        if not entry:
            return None

        path = Path(entry["path"])
        if not path.exists():
            del self._index[key]
            self._save_index()
            return None

        entry["last_accessed"] = time.time()
        self._save_index()
        return path

    def store_layer(self, layer_id: str, source_path: Path, sha256: str = "") -> Path:
        """Store a package layer in the cache."""
        self._maybe_evict()

        dest = self.layers_dir / layer_id
        if source_path != dest:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(str(source_path), str(dest))

        key = f"layer:{layer_id}"
        self._index[key] = {
            "path": str(dest),
            "layer_id": layer_id,
            "sha256": sha256,
            "size": self._dir_size(dest),
            "cached_at": time.time(),
            "last_accessed": time.time(),
            "type": "layer",
        }
        self._save_index()
        return dest

    # ── Metadata Cache ───────────────────────────────────────────────

    def get_metadata(self, package: str) -> dict | None:
        """Get cached package metadata."""
        meta_file = self.metadata_dir / f"{package}.json"
        if not meta_file.exists():
            return None

        try:
            data = json.loads(meta_file.read_text("utf-8"))
            # Check TTL (default 24 hours)
            if time.time() - data.get("_cached_at", 0) > 86400:
                meta_file.unlink(missing_ok=True)
                return None
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def store_metadata(self, package: str, metadata: dict) -> None:
        """Store package metadata."""
        meta_file = self.metadata_dir / f"{package}.json"
        metadata["_cached_at"] = time.time()
        meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # ── Eviction ─────────────────────────────────────────────────────

    def _current_size_mb(self) -> float:
        """Calculate total cache size in MB."""
        total = 0
        for entry in self._index.values():
            total += entry.get("size", 0)
        return total / (1024 * 1024)

    def _maybe_evict(self) -> None:
        """Evict least-recently-used entries if cache is too large."""
        while self._current_size_mb() > self.max_size_mb * 0.9:
            if not self._index:
                break

            # Find LRU entry
            lru_key = min(
                self._index.keys(),
                key=lambda k: self._index[k].get("last_accessed", 0),
            )
            entry = self._index[lru_key]
            path = Path(entry["path"])

            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

            del self._index[lru_key]

        self._save_index()

    @staticmethod
    def _dir_size(path: Path) -> int:
        """Calculate total size of a directory."""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except OSError:
            pass
        return total

    # ── Stats & Maintenance ──────────────────────────────────────────

    def stats(self) -> CacheStats:
        """Get cache usage statistics."""
        wheels = sum(1 for v in self._index.values() if v.get("type") == "wheel")
        layers = sum(1 for v in self._index.values() if v.get("type") == "layer")
        metadata_files = len(list(self.metadata_dir.glob("*.json")))
        current = self._current_size_mb()

        return CacheStats(
            total_size_mb=round(current, 2),
            max_size_mb=self.max_size_mb,
            num_wheels=wheels,
            num_layers=layers,
            num_metadata=metadata_files,
            utilization_pct=round(current / max(self.max_size_mb, 1) * 100, 1),
        )

    def clear(self) -> None:
        """Clear the entire cache."""
        for d in (self.wheels_dir, self.layers_dir, self.metadata_dir):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)
        self._index = {}
        self._save_index()

    def verify_integrity(self) -> list[str]:
        """Verify integrity of all cached items. Returns list of issues."""
        issues: list[str] = []
        for key, entry in list(self._index.items()):
            path = Path(entry["path"])
            if not path.exists():
                issues.append(f"Missing: {key}")
                del self._index[key]
            elif path.is_file() and entry.get("sha256"):
                actual = self._hash_file(path)
                if actual != entry["sha256"]:
                    issues.append(f"Corrupt: {key} (hash mismatch)")
                    path.unlink(missing_ok=True)
                    del self._index[key]

        if issues:
            self._save_index()
        return issues
