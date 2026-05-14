"""
Sandboxed execution environment.

Provides Docker-based isolated execution with resource limits,
network restrictions, and filesystem isolation.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class SandboxConfig:
    memory_limit: str = "4g"
    cpu_limit: float = 4.0
    timeout: int = 600
    network: bool = False
    gpu: bool = False
    image: str = "python:3.11-slim"


@dataclass
class SandboxResult:
    success: bool
    output: Any = None
    stdout: str = ""
    stderr: str = ""
    duration: float = 0
    exit_code: int = 0


class Sandbox:
    """Docker-based execution sandbox."""

    async def execute(self, code: str, config: SandboxConfig | None = None) -> SandboxResult:
        cfg = config or SandboxConfig()
        container_name = f"cpip-exec-{uuid.uuid4().hex[:8]}"
        start = time.time()

        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            f"--memory={cfg.memory_limit}",
            f"--cpus={cfg.cpu_limit}",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
        ]

        if not cfg.network:
            cmd.append("--network=none")
        if cfg.gpu:
            cmd.extend(["--gpus", "all"])

        cmd.extend([cfg.image, "python", "-c", code])

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, timeout=cfg.timeout,
            )
            return SandboxResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration=time.time() - start,
            )
        except subprocess.TimeoutExpired:
            # Kill container
            await asyncio.to_thread(subprocess.run, ["docker", "kill", container_name], capture_output=True)
            return SandboxResult(success=False, stderr="Execution timed out", duration=cfg.timeout)
        except Exception as e:
            return SandboxResult(success=False, stderr=str(e), duration=time.time() - start)


sandbox = Sandbox()
