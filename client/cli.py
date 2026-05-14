"""
cpip CLI — Cloud-Powered Package Intelligence.

Beautiful, feature-rich command-line interface for managing Python packages
with cloud acceleration on Android Termux.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

import typer
from rich.table import Table

from client.config import CpipConfig, load_config, save_config
from client.ui.console import (
    get_console, print_banner, print_cloud, print_divider,
    print_error, print_info, print_success, print_warning,
)

app = typer.Typer(
    name="cpip",
    help="☁️  Cloud-Powered Package Intelligence for Android Termux",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)


def _run(coro):
    """Run an async function synchronously."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, version: bool = typer.Option(False, "--version", "-v", help="Show version")):
    """cpip — Cloud-Powered Package Intelligence."""
    if version:
        from shared.constants import VERSION, CODENAME
        get_console().print(f"  cpip [cpip.primary]v{VERSION}[/cpip.primary] ({CODENAME})")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        print_banner()


# ── Install Command ──────────────────────────────────────────────────

@app.command()
def install(
    packages: list[str] = typer.Argument(..., help="Package(s) to install"),
    version: str = typer.Option("latest", "--version", help="Package version"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reinstall"),
    local_only: bool = typer.Option(False, "--local", help="Local install only, no cloud"),
    cloud_only: bool = typer.Option(False, "--cloud", help="Force cloud execution mode"),
):
    """Install Python packages with cloud acceleration."""
    async def _install():
        config = load_config()
        if local_only:
            config.runtime.offline_mode = True
        from client.cache import CacheManager
        from client.resolver import PackageResolver
        from client.installer import PackageInstaller
        cache = CacheManager(config.cache.max_size_mb)
        resolver = PackageResolver(config, cache)
        installer = PackageInstaller(config, cache, resolver)

        print_divider("Installing Packages")
        failed = []
        for pkg in packages:
            try:
                if cloud_only:
                    from runtime.hooks import register_cloud_package
                    register_cloud_package(pkg, config)
                    print_success(f"{pkg} configured for cloud execution")
                else:
                    await installer.install(pkg, version, force)
            except Exception as e:
                print_error(f"Failed to install {pkg}: {e}")
                failed.append(pkg)
        await resolver.close()
        if failed:
            print_error(f"\n  {len(failed)} package(s) failed: {', '.join(failed)}")
            raise typer.Exit(1)
        print_success(f"\n  {len(packages)} package(s) installed successfully")

    _run(_install())


# ── Shell Command ────────────────────────────────────────────────────

@app.command()
def shell():
    """Launch interactive Python shell with cpip runtime."""
    from client.shell import CpipShell
    config = load_config()
    s = CpipShell(config)
    s.start()


# ── Doctor Command ───────────────────────────────────────────────────

@app.command()
def doctor():
    """Run system diagnostics and health checks."""
    async def _doctor():
        config = load_config()
        from client.cache import CacheManager
        from client.doctor import Doctor
        cache = CacheManager(config.cache.max_size_mb)
        doc = Doctor(config, cache)
        await doc.run_all()
        doc.print_report()

    _run(_doctor())


# ── Sync Command ─────────────────────────────────────────────────────

@app.command()
def sync():
    """Sync package metadata with cloud."""
    async def _sync():
        config = load_config()
        from client.cache import CacheManager
        from client.sync import SyncManager
        cache = CacheManager(config.cache.max_size_mb)
        mgr = SyncManager(config, cache)
        print_cloud("Syncing with cloud registry...")
        result = await mgr.sync_now()
        updated = result.get("metadata_updated", 0)
        errors = result.get("errors", [])
        if errors:
            print_warning(f"Sync completed with errors: {errors[0]}")
        else:
            print_success(f"Synced {updated} package(s)")

    _run(_sync())


# ── GPU Status Command ───────────────────────────────────────────────

@app.command("gpu-status")
def gpu_status():
    """Show GPU runtime availability."""
    from shared.platform import get_system_info
    from client.ui.panels import gpu_status_panel
    console = get_console()
    info = get_system_info()
    gpus = None
    if info.has_gpu:
        gpus = [{"name": "Detected GPU", "memory": "N/A", "status": "available"}]

    console.print()
    console.print(gpu_status_panel(gpus))

    print_divider("Cloud GPU")
    print_cloud("Cloud GPU runtimes: NVIDIA A100, T4, V100")
    print_info("Use `cpip install --cloud torch` for GPU-accelerated packages")
    console.print()


# ── Runtime Command ──────────────────────────────────────────────────

@app.command()
def runtime():
    """Show runtime status dashboard."""
    config = load_config()
    from shared.platform import get_system_info
    from client.ui.panels import dashboard
    from client.daemon import CpipDaemon

    info = get_system_info()
    cloud_connected = CpipDaemon.is_running(config)

    print_banner()
    dashboard(info.__dict__, cloud_connected, config.cloud.api_url)

    from client.cache import CacheManager
    cache = CacheManager(config.cache.max_size_mb)
    stats = cache.stats()
    print_divider("Cache")
    print_info(f"Size: {stats.total_size_mb:.1f}/{stats.max_size_mb}MB ({stats.utilization_pct}%)")
    print_info(f"Wheels: {stats.num_wheels} | Layers: {stats.num_layers} | Metadata: {stats.num_metadata}")
    get_console().print()


# ── Config Command ───────────────────────────────────────────────────

@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current config"),
    init: bool = typer.Option(False, "--init", help="Initialize default config"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Set cloud API URL"),
    offline: Optional[bool] = typer.Option(None, "--offline", help="Toggle offline mode"),
):
    """Manage cpip configuration."""
    cfg = load_config()
    if init:
        save_config(cfg)
        print_success("Configuration initialized")
        return
    if api_url:
        cfg.cloud.api_url = api_url
        save_config(cfg)
        print_success(f"API URL set to {api_url}")
    if offline is not None:
        cfg.runtime.offline_mode = offline
        save_config(cfg)
        print_success(f"Offline mode {'enabled' if offline else 'disabled'}")
    if show or (not api_url and offline is None and not init):
        console = get_console()
        table = Table(title="cpip Configuration", border_style="cpip.divider", header_style="cpip.table.header")
        table.add_column("Setting", style="cpip.primary")
        table.add_column("Value")
        table.add_row("API URL", cfg.cloud.api_url)
        table.add_row("WS URL", cfg.cloud.ws_url)
        table.add_row("Cache Max", f"{cfg.cache.max_size_mb} MB")
        table.add_row("Offline Mode", str(cfg.runtime.offline_mode))
        table.add_row("GPU Offload", str(cfg.runtime.gpu_offload))
        table.add_row("Import Hooks", str(cfg.runtime.import_hooks))
        table.add_row("Auth", "✓ Authenticated" if cfg.auth.token else "✗ Not authenticated")
        console.print()
        console.print(table)
        console.print()


# ── List Command ─────────────────────────────────────────────────────

@app.command("list")
def list_packages():
    """List installed packages."""
    import importlib.metadata
    console = get_console()
    table = Table(title="Installed Packages", border_style="cpip.divider", header_style="cpip.table.header")
    table.add_column("Package", style="cpip.package")
    table.add_column("Version", style="cpip.version")
    for dist in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        table.add_row(dist.metadata["Name"], dist.metadata["Version"])
    console.print()
    console.print(table)
    console.print()


# ── Run Command ──────────────────────────────────────────────────────

@app.command()
def run(script: str = typer.Argument(..., help="Python script to run")):
    """Run a Python script with cpip runtime active."""
    import runpy
    cfg = load_config()
    from runtime.hooks import activate_hooks
    activate_hooks(cfg)
    print_info(f"Running {script} with cpip runtime...")
    try:
        runpy.run_path(script, run_name="__main__")
    except Exception as e:
        print_error(f"Script failed: {e}")
        raise typer.Exit(1)


# ── Daemon Command ───────────────────────────────────────────────────

@app.command()
def daemon(action: str = typer.Argument("status", help="start|stop|status")):
    """Manage the cpip background daemon."""
    from client.daemon import CpipDaemon, run_daemon
    cfg = load_config()
    if action == "start":
        if CpipDaemon.is_running(cfg):
            print_warning("Daemon is already running")
            return
        print_cloud("Starting cpip daemon...")
        import subprocess, os
        subprocess.Popen(
            [sys.executable, "-c", "from client.daemon import run_daemon; run_daemon()"],
            start_new_session=True,
            stdout=open(os.path.join(cfg.log_dir, "daemon.log"), "a"),
            stderr=open(os.path.join(cfg.log_dir, "daemon.err"), "a"),
        )
        print_success("Daemon started")
    elif action == "stop":
        import os
        from pathlib import Path
        pid_file = Path(cfg.home) / "daemon.pid"
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 15)
            print_success("Daemon stopped")
        else:
            print_warning("Daemon is not running")
    else:
        running = CpipDaemon.is_running(cfg)
        if running:
            print_success("Daemon is running")
        else:
            print_warning("Daemon is not running")


# ── Login Command ────────────────────────────────────────────────────

@app.command()
def login(
    api_key: str = typer.Option("", "--api-key", "-k", help="API key for authentication"),
):
    """Authenticate with cpip cloud."""
    async def _login():
        config = load_config()
        if not api_key:
            # Auto-register device in dev mode
            import uuid
            config.auth.device_id = str(uuid.uuid4())
            config.auth.token = f"dev_{config.auth.device_id}"
            from client.config import save_auth
            save_auth(config)
            print_success(f"Dev mode: Device registered ({config.auth.device_id[:8]}...)")
            return
        try:
            import httpx
            async with httpx.AsyncClient(base_url=config.cloud.api_url, timeout=30) as client:
                resp = await client.post("/api/v1/auth/login", json={"api_key": api_key})
                if resp.status_code == 200:
                    data = resp.json()
                    config.auth.token = data["access_token"]
                    config.auth.refresh_token = data.get("refresh_token", "")
                    config.auth.device_id = data.get("device_id", "")
                    from client.config import save_auth
                    save_auth(config)
                    print_success("Authenticated successfully")
                else:
                    print_error(f"Login failed: {resp.text}")
        except Exception as e:
            print_error(f"Login error: {e}")

    _run(_login())


if __name__ == "__main__":
    app()
