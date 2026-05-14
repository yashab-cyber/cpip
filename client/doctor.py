"""
System diagnostics and health check.

Validates the cpip installation, cloud connectivity, cache integrity,
daemon status, and provides actionable fix suggestions.
"""

from __future__ import annotations

import importlib
import shutil
import sys
from dataclasses import dataclass

import httpx

from client.cache import CacheManager
from client.config import CpipConfig
from client.ui.console import get_console, print_error, print_info, print_success, print_warning
from shared.constants import API_V1_PREFIX, VERSION
from shared.platform import get_system_info


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    fix: str = ""


class Doctor:
    """System diagnostic tool for cpip."""

    def __init__(self, config: CpipConfig, cache: CacheManager):
        self.config = config
        self.cache = cache
        self.results: list[CheckResult] = []

    async def run_all(self) -> list[CheckResult]:
        """Run all diagnostic checks."""
        self.results = []
        checks = [
            self._check_python, self._check_platform, self._check_directories,
            self._check_cache, self._check_cloud, self._check_auth,
            self._check_dependencies, self._check_disk,
        ]
        for check in checks:
            try:
                result = await check() if asyncio.iscoroutinefunction(check) else check()
                self.results.append(result)
            except Exception as e:
                self.results.append(CheckResult(name=check.__name__, passed=False, message=str(e)))
        return self.results

    def _check_python(self) -> CheckResult:
        v = sys.version_info
        ok = v.major == 3 and v.minor >= 10
        return CheckResult(
            name="Python Version",
            passed=ok,
            message=f"Python {v.major}.{v.minor}.{v.micro}" + ("" if ok else " (need ≥3.10)"),
            fix="" if ok else "Install Python 3.10+: pkg install python",
        )

    def _check_platform(self) -> CheckResult:
        info = get_system_info()
        return CheckResult(
            name="Platform",
            passed=True,
            message=f"{info.platform_tag} | {info.cpu_count} CPUs | {info.total_memory_mb}MB RAM" + (" | Termux" if info.is_termux else ""),
        )

    def _check_directories(self) -> CheckResult:
        from pathlib import Path
        dirs = [self.config.home, self.config.cache_dir, self.config.wheels_dir, self.config.layers_dir]
        missing = [d for d in dirs if not Path(d).exists()]
        if missing:
            return CheckResult(name="Directories", passed=False, message=f"Missing: {missing}", fix="Run: cpip config --init")
        return CheckResult(name="Directories", passed=True, message="All directories OK")

    def _check_cache(self) -> CheckResult:
        stats = self.cache.stats()
        issues = self.cache.verify_integrity()
        if issues:
            return CheckResult(name="Cache", passed=False, message=f"{len(issues)} integrity issues", fix="Run: cpip cache --repair")
        return CheckResult(
            name="Cache",
            passed=True,
            message=f"{stats.total_size_mb:.1f}/{stats.max_size_mb}MB | {stats.num_wheels} wheels | {stats.num_layers} layers",
        )

    async def _check_cloud(self) -> CheckResult:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.config.cloud.api_url}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    return CheckResult(name="Cloud", passed=True, message=f"Connected | v{data.get('version', '?')}")
        except Exception:
            pass
        return CheckResult(name="Cloud", passed=False, message="Unreachable", fix="Check network or set CPIP_API_URL")

    def _check_auth(self) -> CheckResult:
        if self.config.auth.token:
            return CheckResult(name="Auth", passed=True, message=f"Authenticated (device: {self.config.auth.device_id[:8]}...)")
        return CheckResult(name="Auth", passed=False, message="Not authenticated", fix="Run: cpip login")

    def _check_dependencies(self) -> CheckResult:
        required = ["typer", "rich", "httpx", "websockets", "pydantic"]
        missing = [p for p in required if importlib.util.find_spec(p) is None]
        if missing:
            return CheckResult(name="Dependencies", passed=False, message=f"Missing: {', '.join(missing)}", fix=f"pip install {' '.join(missing)}")
        return CheckResult(name="Dependencies", passed=True, message="All core dependencies OK")

    def _check_disk(self) -> CheckResult:
        info = get_system_info()
        ok = info.available_disk_mb > 500
        return CheckResult(
            name="Disk Space",
            passed=ok,
            message=f"{info.available_disk_mb}MB free" + ("" if ok else " (low!)"),
            fix="" if ok else "Free up disk space or reduce cache: cpip cache --clear",
        )

    def print_report(self) -> None:
        """Print diagnostic report to console."""
        console = get_console()
        console.print(f"\n  [cpip.header]cpip doctor v{VERSION}[/cpip.header]\n")
        passed = sum(1 for r in self.results if r.passed)
        for r in self.results:
            icon = "[cpip.success]✓[/cpip.success]" if r.passed else "[cpip.error]✗[/cpip.error]"
            console.print(f"  {icon} [bold]{r.name}[/bold]: {r.message}")
            if not r.passed and r.fix:
                console.print(f"      [cpip.dim]fix: {r.fix}[/cpip.dim]")
        console.print(f"\n  [cpip.dim]{passed}/{len(self.results)} checks passed[/cpip.dim]\n")


# Need this import at the top for the async check
import asyncio  # noqa: E402
