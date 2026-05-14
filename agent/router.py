"""
AI model routing — decides between local and cloud model execution.

Routes small models to local inference (ONNX, llama.cpp) and
large models to cloud GPU runtimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shared.platform import get_system_info


@dataclass
class ModelInfo:
    name: str
    size_mb: float
    requires_gpu: bool
    local_capable: bool
    provider: str = "cloud"


# Known model size thresholds
LOCAL_MAX_SIZE_MB = 500  # Models under 500MB can run locally

KNOWN_MODELS = {
    "gpt-4": ModelInfo("gpt-4", 0, False, False, "openai"),
    "gpt-3.5-turbo": ModelInfo("gpt-3.5-turbo", 0, False, False, "openai"),
    "llama-2-7b": ModelInfo("llama-2-7b", 3500, True, False, "cloud"),
    "llama-2-13b": ModelInfo("llama-2-13b", 7000, True, False, "cloud"),
    "phi-2": ModelInfo("phi-2", 1400, False, False, "cloud"),
    "tinyllama-1.1b": ModelInfo("tinyllama-1.1b", 600, False, True, "local"),
    "all-MiniLM-L6-v2": ModelInfo("all-MiniLM-L6-v2", 80, False, True, "local"),
    "whisper-tiny": ModelInfo("whisper-tiny", 75, False, True, "local"),
}


class ModelRouter:
    """Routes AI model requests to local or cloud execution."""

    def __init__(self):
        self.system = get_system_info()

    def route(self, model_name: str) -> str:
        """Determine where to run a model. Returns 'local' or 'cloud'."""
        info = KNOWN_MODELS.get(model_name)
        if not info:
            return "cloud"

        if info.provider == "openai":
            return "cloud"  # API-based models always cloud

        if info.local_capable and info.size_mb < LOCAL_MAX_SIZE_MB:
            if self.system.total_memory_mb > info.size_mb * 2:
                return "local"

        return "cloud"

    def get_model_info(self, model_name: str) -> ModelInfo | None:
        return KNOWN_MODELS.get(model_name)

    def list_local_models(self) -> list[str]:
        return [name for name, info in KNOWN_MODELS.items() if info.local_capable]

    def list_cloud_models(self) -> list[str]:
        return [name for name, info in KNOWN_MODELS.items() if not info.local_capable]


model_router = ModelRouter()
