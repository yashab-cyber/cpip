"""Execution pool manager — routes tasks to appropriate runtimes."""

from __future__ import annotations

from typing import Any

from executor.sandbox import sandbox
from executor.gpu_runtime import gpu_runtime
from executor.browser_runtime import browser_runtime


class ExecutionPool:
    """Routes execution requests to the appropriate runtime."""

    async def execute(self, method: str, args: list, kwargs: dict, mode: str = "cloud") -> Any:
        if mode == "gpu" or self._needs_gpu(method):
            if "torch" in method:
                return await gpu_runtime.execute_torch(method, args, kwargs)
            if "tensorflow" in method or "tf." in method:
                return await gpu_runtime.execute_tensorflow(method, args, kwargs)

        if mode == "browser" or "playwright" in method:
            script = kwargs.get("script", "")
            return await browser_runtime.run_playwright(script)

        # Default: general sandbox
        code = self._build_code(method, args, kwargs)
        return await sandbox.execute(code)

    def _needs_gpu(self, method: str) -> bool:
        gpu_indicators = {"torch", "cuda", "tensorflow", "jax", "cupy"}
        return any(g in method.lower() for g in gpu_indicators)

    def _build_code(self, method: str, args: list, kwargs: dict) -> str:
        parts = method.rsplit(".", 1)
        if len(parts) == 2:
            module, func = parts
            return f"import {module}; import json; r = {method}(*{args!r}, **{kwargs!r}); print(json.dumps({{'result': str(r)}}))"
        return f"import json; print(json.dumps({{'result': 'no-op'}}))"


execution_pool = ExecutionPool()
