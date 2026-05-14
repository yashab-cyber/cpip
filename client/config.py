"""
Client configuration management.

Loads/saves TOML configuration from ~/.cpip/config.toml,
provides defaults, and merges environment variable overrides.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import toml as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

from shared.constants import (
    AUTH_FILE,
    CACHE_DIR,
    CONFIG_FILE,
    CPIP_HOME,
    DEFAULT_API_URL,
    DEFAULT_CACHE_MAX_MB,
    DEFAULT_CDN_URL,
    DEFAULT_METADATA_TTL_HOURS,
    DEFAULT_WHEEL_TTL_DAYS,
    DEFAULT_WS_URL,
    LAYERS_DIR,
    LOG_DIR,
    METADATA_DIR,
    VENV_DIR,
    WHEELS_DIR,
)


@dataclass
class CloudConfig:
    """Cloud service connection settings."""
    api_url: str = DEFAULT_API_URL
    ws_url: str = DEFAULT_WS_URL
    cdn_url: str = DEFAULT_CDN_URL
    timeout: int = 30
    max_retries: int = 3


@dataclass
class CacheConfig:
    """Local cache settings."""
    max_size_mb: int = DEFAULT_CACHE_MAX_MB
    wheel_ttl_days: int = DEFAULT_WHEEL_TTL_DAYS
    metadata_ttl_hours: int = DEFAULT_METADATA_TTL_HOURS
    auto_cleanup: bool = True


@dataclass
class RuntimeConfig:
    """Runtime behavior settings."""
    prefer_local: bool = True
    gpu_offload: bool = True
    lazy_loading: bool = True
    cloud_exec: bool = True
    auto_sync: bool = True
    import_hooks: bool = True
    offline_mode: bool = False


@dataclass
class AuthConfig:
    """Authentication state."""
    token: str = ""
    refresh_token: str = ""
    device_id: str = ""
    user_id: str = ""


@dataclass
class CpipConfig:
    """Complete cpip configuration."""
    cloud: CloudConfig = field(default_factory=CloudConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)

    # Computed paths
    home: str = CPIP_HOME
    config_file: str = CONFIG_FILE
    cache_dir: str = CACHE_DIR
    wheels_dir: str = WHEELS_DIR
    layers_dir: str = LAYERS_DIR
    metadata_dir: str = METADATA_DIR
    log_dir: str = LOG_DIR
    venv_dir: str = VENV_DIR
    auth_file: str = AUTH_FILE


def ensure_directories(config: CpipConfig) -> None:
    """Create all required cpip directories."""
    dirs = [
        config.home,
        config.cache_dir,
        config.wheels_dir,
        config.layers_dir,
        config.metadata_dir,
        config.log_dir,
        config.venv_dir,
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def _load_toml(path: str) -> dict[str, Any]:
    """Load a TOML file."""
    if tomllib is None:
        return {}
    filepath = Path(path)
    if not filepath.exists():
        return {}
    try:
        if hasattr(tomllib, "loads"):
            text = filepath.read_text(encoding="utf-8")
            return tomllib.loads(text)  # type: ignore[union-attr]
        else:
            # Python 3.11+ tomllib requires binary mode
            with open(filepath, "rb") as f:
                return tomllib.load(f)  # type: ignore[union-attr]
    except Exception:
        return {}


def _save_toml(path: str, data: dict[str, Any]) -> None:
    """Save a TOML file (simple serializer)."""
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for section, values in data.items():
        if isinstance(values, dict):
            lines.append(f"[{section}]")
            for key, val in values.items():
                if isinstance(val, bool):
                    lines.append(f"{key} = {'true' if val else 'false'}")
                elif isinstance(val, int):
                    lines.append(f"{key} = {val}")
                elif isinstance(val, str):
                    lines.append(f'{key} = "{val}"')
            lines.append("")
    filepath.write_text("\n".join(lines), encoding="utf-8")


def load_config() -> CpipConfig:
    """Load configuration from file + environment variables."""
    config = CpipConfig()
    raw = _load_toml(CONFIG_FILE)

    # Apply TOML values
    if "cloud" in raw:
        cloud = raw["cloud"]
        config.cloud.api_url = cloud.get("api_url", config.cloud.api_url)
        config.cloud.ws_url = cloud.get("ws_url", config.cloud.ws_url)
        config.cloud.cdn_url = cloud.get("cdn_url", config.cloud.cdn_url)
        config.cloud.timeout = cloud.get("timeout", config.cloud.timeout)

    if "cache" in raw:
        cache = raw["cache"]
        config.cache.max_size_mb = cache.get("max_size_mb", config.cache.max_size_mb)
        config.cache.wheel_ttl_days = cache.get("wheel_ttl_days", config.cache.wheel_ttl_days)

    if "runtime" in raw:
        rt = raw["runtime"]
        config.runtime.prefer_local = rt.get("prefer_local", config.runtime.prefer_local)
        config.runtime.gpu_offload = rt.get("gpu_offload", config.runtime.gpu_offload)
        config.runtime.lazy_loading = rt.get("lazy_loading", config.runtime.lazy_loading)
        config.runtime.cloud_exec = rt.get("cloud_exec", config.runtime.cloud_exec)
        config.runtime.offline_mode = rt.get("offline_mode", config.runtime.offline_mode)

    # Environment variable overrides (highest priority)
    if api_url := os.getenv("CPIP_API_URL"):
        config.cloud.api_url = api_url
    if ws_url := os.getenv("CPIP_WS_URL"):
        config.cloud.ws_url = ws_url
    if os.getenv("CPIP_OFFLINE"):
        config.runtime.offline_mode = True

    # Load auth state
    auth_path = Path(AUTH_FILE)
    if auth_path.exists():
        try:
            auth_data = json.loads(auth_path.read_text(encoding="utf-8"))
            config.auth.token = auth_data.get("token", "")
            config.auth.refresh_token = auth_data.get("refresh_token", "")
            config.auth.device_id = auth_data.get("device_id", "")
            config.auth.user_id = auth_data.get("user_id", "")
        except Exception:
            pass

    ensure_directories(config)
    return config


def save_config(config: CpipConfig) -> None:
    """Persist configuration to disk."""
    data = {
        "cloud": {
            "api_url": config.cloud.api_url,
            "ws_url": config.cloud.ws_url,
            "cdn_url": config.cloud.cdn_url,
            "timeout": config.cloud.timeout,
        },
        "cache": {
            "max_size_mb": config.cache.max_size_mb,
            "wheel_ttl_days": config.cache.wheel_ttl_days,
            "auto_cleanup": config.cache.auto_cleanup,
        },
        "runtime": {
            "prefer_local": config.runtime.prefer_local,
            "gpu_offload": config.runtime.gpu_offload,
            "lazy_loading": config.runtime.lazy_loading,
            "cloud_exec": config.runtime.cloud_exec,
            "offline_mode": config.runtime.offline_mode,
        },
    }
    _save_toml(CONFIG_FILE, data)


def save_auth(config: CpipConfig) -> None:
    """Persist auth state to disk."""
    auth_path = Path(AUTH_FILE)
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    auth_data = {
        "token": config.auth.token,
        "refresh_token": config.auth.refresh_token,
        "device_id": config.auth.device_id,
        "user_id": config.auth.user_id,
    }
    auth_path.write_text(json.dumps(auth_data, indent=2), encoding="utf-8")
    os.chmod(str(auth_path), 0o600)
