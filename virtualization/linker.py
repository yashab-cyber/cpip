"""
Dynamic linker for shared objects (.so files).

Downloads, caches, and configures native libraries required by
virtualized packages, handling LD_LIBRARY_PATH and RPATH patching.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from shared.constants import CPIP_HOME


class DynamicLinker:
    """Manages shared object dependencies for virtualized packages."""

    def __init__(self, lib_dir: str | None = None):
        self.lib_dir = Path(lib_dir or os.path.join(CPIP_HOME, "lib"))
        self.lib_dir.mkdir(parents=True, exist_ok=True)
        self._loaded: set[str] = set()

    def install_so(self, name: str, data: bytes) -> Path:
        """Install a shared object file to the lib directory."""
        dest = self.lib_dir / name
        dest.write_bytes(data)
        dest.chmod(0o755)
        self._loaded.add(name)
        return dest

    def get_so_path(self, name: str) -> Path | None:
        path = self.lib_dir / name
        return path if path.exists() else None

    def configure_env(self) -> dict[str, str]:
        """Get environment variables for dynamic linking."""
        lib_path = str(self.lib_dir)
        current = os.environ.get("LD_LIBRARY_PATH", "")
        paths = [lib_path] + [p for p in current.split(":") if p and p != lib_path]
        return {"LD_LIBRARY_PATH": ":".join(paths)}

    def activate(self) -> None:
        """Add lib_dir to current process's LD_LIBRARY_PATH."""
        env = self.configure_env()
        os.environ["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH"]

    def patch_rpath(self, binary_path: str) -> bool:
        """Patch RPATH of a binary to include cpip lib dir."""
        if not shutil.which("patchelf"):
            return False
        try:
            subprocess.run(
                ["patchelf", "--set-rpath", str(self.lib_dir), binary_path],
                capture_output=True, timeout=30, check=True,
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def list_dependencies(self, binary_path: str) -> list[str]:
        """List shared object dependencies of a binary."""
        try:
            result = subprocess.run(
                ["ldd", binary_path], capture_output=True, text=True, timeout=10,
            )
            deps = []
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if parts and parts[0].endswith(".so") or ".so." in parts[0]:
                    deps.append(parts[0])
            return deps
        except Exception:
            return []

    def verify_dependencies(self, binary_path: str) -> list[str]:
        """Check for missing dependencies. Returns list of missing .so names."""
        missing = []
        try:
            result = subprocess.run(
                ["ldd", binary_path], capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.splitlines():
                if "not found" in line:
                    parts = line.strip().split()
                    if parts:
                        missing.append(parts[0])
        except Exception:
            pass
        return missing
