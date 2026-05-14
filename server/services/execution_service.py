"""
Execution service — manages remote code execution.

Handles execution requests, sandbox management, and result collection.
"""

from __future__ import annotations

import time
import traceback
from typing import Any

from shared.models import ExecutionRequest, ExecutionResult, ExecutionStatus


class ExecutionService:
    """Remote execution management."""

    def __init__(self):
        self._results: dict[str, ExecutionResult] = {}

    async def execute(self, req: ExecutionRequest) -> ExecutionResult:
        """Execute a remote function call in a sandbox."""
        start = time.time()
        try:
            # In development: execute locally in-process
            # Production: Docker sandbox or Firecracker microVM
            result = await self._execute_sandboxed(req)
            duration = (time.time() - start) * 1000
            exec_result = ExecutionResult(
                request_id=req.request_id,
                status=ExecutionStatus.COMPLETED,
                result=result,
                duration_ms=round(duration, 2),
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            exec_result = ExecutionResult(
                request_id=req.request_id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                traceback=traceback.format_exc(),
                duration_ms=round(duration, 2),
            )
        self._results[req.request_id] = exec_result
        return exec_result

    async def _execute_sandboxed(self, req: ExecutionRequest) -> Any:
        """Execute in sandbox. Dev mode: direct execution."""
        method_parts = req.method.split(".")
        if len(method_parts) < 2:
            raise ValueError(f"Invalid method: {req.method}")

        module_name = method_parts[0]
        func_path = ".".join(method_parts[1:])

        # Dynamic import and execution
        import importlib
        mod = importlib.import_module(module_name)
        obj = mod
        for attr in method_parts[1:]:
            obj = getattr(obj, attr)

        if callable(obj):
            return obj(*req.args, **req.kwargs)
        return obj

    async def get_result(self, execution_id: str) -> ExecutionResult | None:
        return self._results.get(execution_id)

    async def cancel(self, execution_id: str) -> None:
        result = self._results.get(execution_id)
        if result and result.status in (ExecutionStatus.PENDING, ExecutionStatus.RUNNING):
            result.status = ExecutionStatus.CANCELLED


execution_service = ExecutionService()
