"""
Virtual package mount system.

Creates virtual package directories by composing cached layers
and mounting them into Python's import path.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from virtualization.layers import LayerManager, PackageManifest


class VirtualMount:
    """Mounts virtualized packages into Python's import path."""

    def __init__(self, layer_manager: LayerManager):
        self.layer_manager = layer_manager
        self._mounts: dict[str, Path] = {}

    def mount(self, manifest: PackageManifest) -> Path:
        """Mount a package's layers into the import path."""
        if manifest.name in self._mounts:
            return self._mounts[manifest.name]

        composed = self.layer_manager.compose_layers(manifest.layers)
        if str(composed) not in sys.path:
            sys.path.insert(0, str(composed))
        self._mounts[manifest.name] = composed
        return composed

    def unmount(self, package_name: str) -> None:
        """Remove a mounted package from the import path."""
        mount_path = self._mounts.pop(package_name, None)
        if mount_path and str(mount_path) in sys.path:
            sys.path.remove(str(mount_path))
        # Also remove from sys.modules
        to_remove = [k for k in sys.modules if k == package_name or k.startswith(f"{package_name}.")]
        for key in to_remove:
            del sys.modules[key]

    def is_mounted(self, package_name: str) -> bool:
        return package_name in self._mounts

    def list_mounts(self) -> dict[str, str]:
        return {name: str(path) for name, path in self._mounts.items()}

    def unmount_all(self) -> None:
        for name in list(self._mounts.keys()):
            self.unmount(name)
