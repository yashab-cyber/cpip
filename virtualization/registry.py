"""
Package metadata registry for virtualized packages.

Maintains a local catalog of available virtual packages with
their layer manifests, fetched from the cloud registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared.constants import METADATA_DIR
from virtualization.layers import PackageLayer, PackageManifest


class PackageRegistry:
    """Local registry of virtual package manifests."""

    def __init__(self, metadata_dir: str = METADATA_DIR):
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, PackageManifest] = {}

    def get(self, name: str) -> PackageManifest | None:
        if name in self._cache:
            return self._cache[name]
        manifest_file = self.metadata_dir / f"{name}.manifest.json"
        if not manifest_file.exists():
            return None
        try:
            data = json.loads(manifest_file.read_text("utf-8"))
            manifest = self._parse_manifest(data)
            self._cache[name] = manifest
            return manifest
        except Exception:
            return None

    def store(self, manifest: PackageManifest) -> None:
        data = {
            "name": manifest.name,
            "version": manifest.version,
            "entry_point": manifest.entry_point,
            "python_requires": manifest.python_requires,
            "dependencies": manifest.dependencies,
            "layers": [
                {
                    "layer_id": l.layer_id, "sha256": l.sha256,
                    "size": l.size, "content_type": l.content_type,
                    "files": l.files,
                }
                for l in manifest.layers
            ],
        }
        path = self.metadata_dir / f"{manifest.name}.manifest.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._cache[manifest.name] = manifest

    def list_packages(self) -> list[str]:
        return [
            p.stem.replace(".manifest", "")
            for p in self.metadata_dir.glob("*.manifest.json")
        ]

    def remove(self, name: str) -> None:
        path = self.metadata_dir / f"{name}.manifest.json"
        path.unlink(missing_ok=True)
        self._cache.pop(name, None)

    @staticmethod
    def _parse_manifest(data: dict) -> PackageManifest:
        layers = [
            PackageLayer(
                layer_id=l["layer_id"], sha256=l["sha256"],
                size=l["size"], content_type=l.get("content_type", "python"),
                files=l.get("files", []),
            )
            for l in data.get("layers", [])
        ]
        return PackageManifest(
            name=data["name"], version=data["version"],
            layers=layers, entry_point=data.get("entry_point", ""),
            python_requires=data.get("python_requires", ""),
            dependencies=data.get("dependencies", []),
        )
