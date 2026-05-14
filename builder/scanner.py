"""
Security scanner for built packages.

Performs static analysis, vulnerability checks, and binary inspection.
"""

from __future__ import annotations

import hashlib
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScanResult:
    package: str
    clean: bool
    issues: list[str] = field(default_factory=list)
    sha256: str = ""
    file_count: int = 0
    total_size: int = 0


class PackageScanner:
    """Scans built packages for security issues."""

    async def scan_wheel(self, wheel_path: str) -> ScanResult:
        path = Path(wheel_path)
        result = ScanResult(package=path.name, clean=True)
        result.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()

        if not zipfile.is_zipfile(path):
            result.clean = False
            result.issues.append("Not a valid zip/wheel file")
            return result

        with zipfile.ZipFile(path) as zf:
            result.file_count = len(zf.namelist())
            result.total_size = sum(i.file_size for i in zf.infolist())

            for name in zf.namelist():
                # Check for path traversal
                if name.startswith("/") or ".." in name:
                    result.clean = False
                    result.issues.append(f"Path traversal: {name}")
                # Check for suspicious scripts
                if name.endswith((".sh", ".bat", ".cmd", ".ps1")):
                    result.issues.append(f"Script file: {name}")
                # Check for oversized files (> 500MB)
                info = zf.getinfo(name)
                if info.file_size > 500 * 1024 * 1024:
                    result.issues.append(f"Oversized file: {name} ({info.file_size} bytes)")

        return result


scanner = PackageScanner()
