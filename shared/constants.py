"""
cpip system-wide constants.

Central registry for API endpoints, default paths, version info,
and architecture identifiers used across client and server.
"""

from __future__ import annotations

import os

# ── Version ──────────────────────────────────────────────────────────
VERSION = "0.1.0"
CODENAME = "nebula"

# ── Cloud Endpoints ──────────────────────────────────────────────────
DEFAULT_API_URL = os.getenv("CPIP_API_URL", "http://localhost:8000")
DEFAULT_WS_URL = os.getenv("CPIP_WS_URL", "ws://localhost:8000/ws")
DEFAULT_CDN_URL = os.getenv("CPIP_CDN_URL", "http://localhost:8000/cdn")

# ── API Routes ───────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"
WS_ENDPOINT = "/ws"
HEALTH_ENDPOINT = "/health"

# ── Local Paths ──────────────────────────────────────────────────────
CPIP_HOME = os.path.expanduser(os.getenv("CPIP_HOME", "~/.cpip"))
CACHE_DIR = os.path.join(CPIP_HOME, "cache")
WHEELS_DIR = os.path.join(CACHE_DIR, "wheels")
LAYERS_DIR = os.path.join(CACHE_DIR, "layers")
METADATA_DIR = os.path.join(CACHE_DIR, "metadata")
CONFIG_FILE = os.path.join(CPIP_HOME, "config.toml")
AUTH_FILE = os.path.join(CPIP_HOME, "auth.json")
LOG_DIR = os.path.join(CPIP_HOME, "logs")
VENV_DIR = os.path.join(CPIP_HOME, "envs")

# ── Architecture ─────────────────────────────────────────────────────
SUPPORTED_ARCHITECTURES = ("aarch64", "armv7l", "x86_64", "arm64")
TERMUX_PREFIX = "/data/data/com.termux/files/usr"

# ── Package Strategies ───────────────────────────────────────────────
STRATEGY_LOCAL = "local_install"
STRATEGY_TERMUX_PKG = "termux_pkg"
STRATEGY_CLOUD_WHEEL = "cloud_wheel"
STRATEGY_CLOUD_BUILD = "cloud_build"
STRATEGY_CLOUD_EXEC = "cloud_exec"
STRATEGY_HYBRID = "hybrid"

# ── WebSocket / RPC ──────────────────────────────────────────────────
WS_HEARTBEAT_INTERVAL = 30  # seconds
WS_RECONNECT_BASE_DELAY = 1  # seconds
WS_RECONNECT_MAX_DELAY = 60  # seconds
WS_MAX_MESSAGE_SIZE = 64 * 1024 * 1024  # 64 MB
RPC_TIMEOUT = 300  # 5 minutes default

# ── Cache Settings ───────────────────────────────────────────────────
DEFAULT_CACHE_MAX_MB = 2048
DEFAULT_WHEEL_TTL_DAYS = 30
DEFAULT_METADATA_TTL_HOURS = 24

# ── Build System ─────────────────────────────────────────────────────
BUILD_TIMEOUT = 3600  # 1 hour
BUILD_MAX_RETRIES = 3
BUILDER_DOCKER_IMAGE = "cpip/builder:latest"
BUILDER_ARM64_IMAGE = "cpip/builder-arm64:latest"

# ── Execution ────────────────────────────────────────────────────────
EXEC_TIMEOUT = 600  # 10 minutes
EXEC_MAX_MEMORY_MB = 4096
EXEC_MAX_CPU_CORES = 4
GPU_RUNTIME_IMAGE = "cpip/gpu-runtime:latest"
BROWSER_RUNTIME_IMAGE = "cpip/browser-runtime:latest"

# ── Security ─────────────────────────────────────────────────────────
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30
RATE_LIMIT_DEFAULT = "100/minute"
PACKAGE_SIGN_ALGORITHM = "ed25519"

# ── Heavy Packages (require cloud strategies) ────────────────────────
CLOUD_PREFERRED_PACKAGES = frozenset({
    "torch", "torchvision", "torchaudio",
    "tensorflow", "tensorflow-gpu",
    "jax", "jaxlib",
    "opencv-python", "opencv-contrib-python",
    "scipy",
    "playwright",
    "chromium",
    "llama-cpp-python",
    "transformers",
    "diffusers",
    "triton",
    "cupy",
    "dlib",
    "mediapipe",
    "onnxruntime",
    "paddlepaddle",
})

# ── ASCII Art ────────────────────────────────────────────────────────
BANNER = r"""
[bold cyan]
   ██████╗██████╗ ██╗██████╗
  ██╔════╝██╔══██╗██║██╔══██╗
  ██║     ██████╔╝██║██████╔╝
  ██║     ██╔═══╝ ██║██╔═══╝
  ╚██████╗██║     ██║██║
   ╚═════╝╚═╝     ╚═╝╚═╝
[/bold cyan]
[dim]  Cloud-Powered Package Intelligence[/dim]
[dim]  v{version} • {codename}[/dim]
"""
