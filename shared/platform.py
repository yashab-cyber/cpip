"""
Platform detection and system capability profiling.

Detects whether we're running on Termux/Android, system architecture,
available resources, and device capabilities.
"""

from __future__ import annotations

import os
import platform
import shutil
import struct
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class SystemInfo:
    """Immutable snapshot of system capabilities."""

    is_termux: bool
    is_android: bool
    architecture: str
    python_version: str
    pointer_size: int  # 32 or 64 bit
    cpu_count: int
    total_memory_mb: int
    available_disk_mb: int
    termux_prefix: str | None
    home_dir: str
    has_gpu: bool
    has_docker: bool
    platform_tag: str  # e.g. "android_aarch64", "linux_x86_64"
    extra: dict = field(default_factory=dict)


def detect_termux() -> bool:
    """Check if running inside Termux on Android."""
    indicators = [
        os.getenv("PREFIX", "").startswith("/data/data/com.termux"),
        os.path.isdir("/data/data/com.termux"),
        os.getenv("TERMUX_VERSION") is not None,
        "com.termux" in os.getenv("HOME", ""),
    ]
    return any(indicators)


def detect_android() -> bool:
    """Check if running on Android (may or may not be Termux)."""
    indicators = [
        os.path.isfile("/system/build.prop"),
        os.path.isdir("/data/data"),
        "android" in platform.platform().lower(),
        "Android" in platform.release(),
    ]
    return any(indicators) or detect_termux()


def get_architecture() -> str:
    """Get normalized CPU architecture string."""
    machine = platform.machine().lower()
    arch_map = {
        "aarch64": "aarch64",
        "arm64": "aarch64",
        "armv8l": "aarch64",
        "armv7l": "armv7l",
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "i686": "x86",
        "i386": "x86",
    }
    return arch_map.get(machine, machine)


def get_cpu_count() -> int:
    """Get number of available CPUs."""
    try:
        return os.cpu_count() or 1
    except Exception:
        return 1


def get_total_memory_mb() -> int:
    """Get total system memory in MB."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb // 1024
    except Exception:
        pass
    return 0


def get_available_disk_mb(path: str | None = None) -> int:
    """Get available disk space in MB at the given path."""
    target = path or os.path.expanduser("~")
    try:
        usage = shutil.disk_usage(target)
        return int(usage.free / (1024 * 1024))
    except Exception:
        return 0


def has_gpu() -> bool:
    """Check if GPU acceleration is potentially available."""
    indicators = [
        os.path.exists("/dev/kgsl-3d0"),  # Qualcomm Adreno (Android)
        os.path.exists("/dev/mali0"),  # ARM Mali
        os.path.exists("/dev/nvidia0"),  # NVIDIA
        os.path.exists("/proc/driver/nvidia"),
        shutil.which("nvidia-smi") is not None,
        os.getenv("CUDA_HOME") is not None,
    ]
    return any(indicators)


def has_docker() -> bool:
    """Check if Docker is available."""
    return shutil.which("docker") is not None


def get_platform_tag() -> str:
    """Generate platform compatibility tag (e.g. 'android_aarch64')."""
    arch = get_architecture()
    if detect_android():
        return f"android_{arch}"
    system = platform.system().lower()
    return f"{system}_{arch}"


def get_termux_prefix() -> str | None:
    """Get Termux prefix path if running in Termux."""
    prefix = os.getenv("PREFIX")
    if prefix and "com.termux" in prefix:
        return prefix
    if os.path.isdir("/data/data/com.termux/files/usr"):
        return "/data/data/com.termux/files/usr"
    return None


@lru_cache(maxsize=1)
def get_system_info() -> SystemInfo:
    """Gather complete system information (cached)."""
    return SystemInfo(
        is_termux=detect_termux(),
        is_android=detect_android(),
        architecture=get_architecture(),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        pointer_size=struct.calcsize("P") * 8,
        cpu_count=get_cpu_count(),
        total_memory_mb=get_total_memory_mb(),
        available_disk_mb=get_available_disk_mb(),
        termux_prefix=get_termux_prefix(),
        home_dir=str(Path.home()),
        has_gpu=has_gpu(),
        has_docker=has_docker(),
        platform_tag=get_platform_tag(),
    )


def print_system_info() -> None:
    """Print system information for diagnostics."""
    info = get_system_info()
    print(f"  Platform:      {info.platform_tag}")
    print(f"  Architecture:  {info.architecture} ({info.pointer_size}-bit)")
    print(f"  Python:        {info.python_version}")
    print(f"  Termux:        {'Yes' if info.is_termux else 'No'}")
    print(f"  Android:       {'Yes' if info.is_android else 'No'}")
    print(f"  CPUs:          {info.cpu_count}")
    print(f"  Memory:        {info.total_memory_mb} MB")
    print(f"  Disk free:     {info.available_disk_mb} MB")
    print(f"  GPU:           {'Detected' if info.has_gpu else 'None'}")
    print(f"  Docker:        {'Available' if info.has_docker else 'Not found'}")
    if info.termux_prefix:
        print(f"  Termux prefix: {info.termux_prefix}")
