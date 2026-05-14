"""
Execution scheduler — decides where code runs: local, cloud, or hybrid.

Uses heuristics based on package type, operation complexity,
device capabilities, and cloud availability.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from shared.constants import CLOUD_PREFERRED_PACKAGES
from shared.models import ExecutionMode
from shared.platform import get_system_info


class SchedulerDecision(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"
    GPU = "gpu"


@dataclass
class ScheduleResult:
    decision: SchedulerDecision
    reason: str
    priority: int = 5  # 1=highest


class ExecutionScheduler:
    """Decides where to execute operations based on heuristics."""

    def __init__(self, config: Any = None):
        self.config = config
        self.system = get_system_info()

    def schedule(self, method: str, args: tuple = (), kwargs: dict | None = None) -> ScheduleResult:
        """Determine execution target for a method call."""
        top_package = method.split(".")[0]

        # GPU-required operations
        if self._needs_gpu(method):
            if self.system.has_gpu:
                return ScheduleResult(SchedulerDecision.LOCAL, "Local GPU available")
            return ScheduleResult(SchedulerDecision.GPU, "GPU operation → cloud GPU", priority=2)

        # Cloud-preferred packages
        if top_package in CLOUD_PREFERRED_PACKAGES:
            return ScheduleResult(SchedulerDecision.CLOUD, f"{top_package} is cloud-preferred", priority=3)

        # Large data operations
        if self._is_large_operation(args, kwargs):
            return ScheduleResult(SchedulerDecision.CLOUD, "Large data operation", priority=4)

        # Default: local
        return ScheduleResult(SchedulerDecision.LOCAL, "Standard local execution", priority=8)

    def _needs_gpu(self, method: str) -> bool:
        gpu_methods = {"cuda", "gpu", "to('cuda')", ".cuda()", "npu"}
        gpu_packages = {"torch", "tensorflow", "jax", "cupy"}
        top = method.split(".")[0]
        return top in gpu_packages or any(g in method.lower() for g in gpu_methods)

    def _is_large_operation(self, args: tuple, kwargs: dict | None) -> bool:
        """Check if operation involves large data."""
        total_size = 0
        for arg in args:
            total_size += self._estimate_size(arg)
        if total_size > 100 * 1024 * 1024:  # > 100MB
            return True
        return False

    @staticmethod
    def _estimate_size(obj: Any) -> int:
        """Estimate memory size of an object."""
        import sys as _sys
        try:
            if hasattr(obj, "nbytes"):  # numpy array
                return obj.nbytes
            if hasattr(obj, "nelement"):  # torch tensor
                return obj.nelement() * 4
            return _sys.getsizeof(obj)
        except Exception:
            return 0
