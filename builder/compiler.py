"""
Cross-compilation engine for ARM64 Android.

Manages Docker-based cross-compilation using Android NDK toolchains.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CompileResult:
    success: bool
    wheel_path: str | None = None
    log: str = ""
    error: str = ""
    duration: float = 0


class CrossCompiler:
    """Cross-compiles Python packages for ARM64 Android."""

    def __init__(self, docker_image: str = "cpip/builder-arm64:latest"):
        self.docker_image = docker_image

    async def compile(
        self, package: str, version: str = "latest",
        python_version: str = "3.11", target_arch: str = "aarch64",
    ) -> CompileResult:
        """Compile a package using Docker cross-compilation."""
        import asyncio
        import time

        start = time.time()
        version_spec = f"=={version}" if version != "latest" else ""

        cmd = [
            "docker", "run", "--rm",
            "-e", f"PACKAGE={package}{version_spec}",
            "-e", f"PYTHON_VERSION={python_version}",
            "-e", f"TARGET_ARCH={target_arch}",
            "-v", "/tmp/cpip-builds:/output",
            self.docker_image,
            "build",
        ]

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, timeout=3600,
            )
            duration = time.time() - start

            if result.returncode == 0:
                # Find output wheel
                output_dir = Path("/tmp/cpip-builds")
                wheels = list(output_dir.glob(f"{package.replace('-', '_')}*.whl"))
                wheel_path = str(wheels[0]) if wheels else None
                return CompileResult(success=True, wheel_path=wheel_path, log=result.stdout, duration=duration)
            else:
                return CompileResult(success=False, log=result.stdout, error=result.stderr, duration=duration)
        except subprocess.TimeoutExpired:
            return CompileResult(success=False, error="Build timed out (1hr limit)", duration=3600)
        except Exception as e:
            return CompileResult(success=False, error=str(e), duration=time.time() - start)


compiler = CrossCompiler()
