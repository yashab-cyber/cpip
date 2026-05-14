"""
Pydantic models shared between client and server.

These define the wire format for API requests/responses, package metadata,
build/execution jobs, device profiles, and session state.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────

class PackageStrategy(str, Enum):
    """How a package should be provided to the client."""
    LOCAL_INSTALL = "local_install"
    TERMUX_PKG = "termux_pkg"
    CLOUD_WHEEL = "cloud_wheel"
    CLOUD_BUILD = "cloud_build"
    CLOUD_EXEC = "cloud_exec"
    HYBRID = "hybrid"


class BuildStatus(str, Enum):
    """Status of a cloud build job."""
    QUEUED = "queued"
    BUILDING = "building"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    """Status of a remote execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ExecutionMode(str, Enum):
    """Where code will execute."""
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"
    GPU = "gpu"
    BROWSER = "browser"


# ── Device / Platform ────────────────────────────────────────────────

class DeviceInfo(BaseModel):
    """Information about the client device."""
    device_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    architecture: str
    platform_tag: str
    python_version: str
    cpu_count: int = 1
    total_memory_mb: int = 0
    available_disk_mb: int = 0
    is_termux: bool = False
    is_android: bool = False
    has_gpu: bool = False
    cpip_version: str = ""


# ── Package ──────────────────────────────────────────────────────────

class PackageInfo(BaseModel):
    """Package metadata from the cloud registry."""
    name: str
    version: str
    description: str = ""
    strategy: PackageStrategy = PackageStrategy.LOCAL_INSTALL
    wheel_url: str | None = None
    wheel_hash: str | None = None
    wheel_size: int = 0
    layers: list[LayerInfo] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    supported_architectures: list[str] = Field(default_factory=list)
    requires_gpu: bool = False
    cloud_only: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class LayerInfo(BaseModel):
    """A single package layer (for virtualized packages)."""
    layer_id: str
    url: str
    sha256: str
    size: int
    content_type: str = "python"  # python, native, data
    compressed: bool = True


class PackageResolution(BaseModel):
    """Result of resolving how to provide a package."""
    package: str
    version: str
    strategy: PackageStrategy
    info: PackageInfo | None = None
    fallback_strategies: list[PackageStrategy] = Field(default_factory=list)
    reason: str = ""


# ── Build ────────────────────────────────────────────────────────────

class BuildRequest(BaseModel):
    """Request to build a package on the cloud build farm."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    package_name: str
    package_version: str = "latest"
    target_architecture: str = "aarch64"
    python_version: str = "3.11"
    build_options: dict[str, Any] = Field(default_factory=dict)
    priority: int = 5  # 1 = highest, 10 = lowest
    created_at: float = Field(default_factory=time.time)


class BuildResult(BaseModel):
    """Result of a cloud build."""
    request_id: str
    status: BuildStatus
    package_name: str
    package_version: str
    wheel_url: str | None = None
    wheel_hash: str | None = None
    wheel_size: int = 0
    build_log: str = ""
    duration_seconds: float = 0
    error: str | None = None


# ── Execution ────────────────────────────────────────────────────────

class ExecutionRequest(BaseModel):
    """Request to execute code remotely."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    method: str  # e.g. "torch.tensor"
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    mode: ExecutionMode = ExecutionMode.CLOUD
    timeout: int = 300  # seconds
    session_id: str | None = None
    requires_gpu: bool = False


class ExecutionResult(BaseModel):
    """Result of remote execution."""
    request_id: str
    status: ExecutionStatus
    result: Any = None
    result_type: str = "python"  # python, tensor, image, stream
    result_metadata: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0
    error: str | None = None
    traceback: str | None = None


# ── Session ──────────────────────────────────────────────────────────

class SessionInfo(BaseModel):
    """Active client-cloud session."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str
    created_at: float = Field(default_factory=time.time)
    last_active: float = Field(default_factory=time.time)
    execution_mode: ExecutionMode = ExecutionMode.LOCAL
    active_packages: list[str] = Field(default_factory=list)
    cloud_modules: list[str] = Field(default_factory=list)


# ── Auth ─────────────────────────────────────────────────────────────

class AuthToken(BaseModel):
    """Authentication token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserInfo(BaseModel):
    """User profile information."""
    user_id: str
    email: str | None = None
    api_key: str | None = None
    devices: list[str] = Field(default_factory=list)
    tier: str = "free"  # free, pro, enterprise


# ── Health ───────────────────────────────────────────────────────────

class HealthStatus(BaseModel):
    """System health check response."""
    status: str = "ok"
    version: str
    uptime_seconds: float = 0
    services: dict[str, str] = Field(default_factory=dict)  # service -> status
    build_queue_size: int = 0
    active_executions: int = 0
    connected_devices: int = 0
