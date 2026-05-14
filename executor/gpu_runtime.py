"""GPU execution runtime for cloud-accelerated ML operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from executor.sandbox import Sandbox, SandboxConfig, SandboxResult


@dataclass
class GPUInfo:
    name: str
    memory_mb: int
    utilization_pct: float
    available: bool


class GPURuntime:
    """Manages GPU-accelerated execution in cloud containers."""

    def __init__(self):
        self._sandbox = Sandbox()

    async def execute_torch(self, method: str, args: list, kwargs: dict) -> SandboxResult:
        code = self._build_torch_code(method, args, kwargs)
        config = SandboxConfig(gpu=True, image="pytorch/pytorch:latest", memory_limit="8g")
        return await self._sandbox.execute(code, config)

    async def execute_tensorflow(self, method: str, args: list, kwargs: dict) -> SandboxResult:
        code = self._build_tf_code(method, args, kwargs)
        config = SandboxConfig(gpu=True, image="tensorflow/tensorflow:latest-gpu", memory_limit="8g")
        return await self._sandbox.execute(code, config)

    async def list_gpus(self) -> list[GPUInfo]:
        result = await self._sandbox.execute(
            "import subprocess; print(subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,utilization.gpu', '--format=csv,noheader'], capture_output=True, text=True).stdout)",
            SandboxConfig(gpu=True),
        )
        gpus = []
        if result.success:
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    gpus.append(GPUInfo(
                        name=parts[0], memory_mb=int(parts[1].replace(" MiB", "")),
                        utilization_pct=float(parts[2].replace(" %", "")), available=True,
                    ))
        return gpus

    def _build_torch_code(self, method: str, args: list, kwargs: dict) -> str:
        return f"""
import torch, json, sys
result = {method}(*{args!r}, **{kwargs!r})
if hasattr(result, 'tolist'): result = result.tolist()
print(json.dumps({{"result": result}}))
"""

    def _build_tf_code(self, method: str, args: list, kwargs: dict) -> str:
        return f"""
import tensorflow as tf, json
result = {method}(*{args!r}, **{kwargs!r})
if hasattr(result, 'numpy'): result = result.numpy().tolist()
print(json.dumps({{"result": result}}))
"""


gpu_runtime = GPURuntime()
