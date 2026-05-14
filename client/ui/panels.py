"""
Rich status panels and dashboard components.

Provides formatted panels for system status, package info,
GPU availability, and runtime diagnostics.
"""

from __future__ import annotations

from typing import Any

from rich.align import Align
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from client.ui.console import get_console


def status_panel(title: str, items: dict[str, str], border_style: str = "cyan") -> Panel:
    """Create a status panel with key-value pairs."""
    table = Table(show_header=False, show_edge=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cpip.dim", min_width=18)
    table.add_column("Value")

    for key, value in items.items():
        table.add_row(key, value)

    return Panel(
        table,
        title=f"[cpip.header]{title}[/cpip.header]",
        border_style=border_style,
        padding=(1, 2),
    )


def system_info_panel(info: dict[str, Any]) -> Panel:
    """Create a system information panel."""
    status_items = {
        "Platform": f"[cpip.primary]{info.get('platform_tag', 'unknown')}[/cpip.primary]",
        "Architecture": info.get("architecture", "unknown"),
        "Python": info.get("python_version", "unknown"),
        "CPU Cores": str(info.get("cpu_count", 0)),
        "Memory": f"{info.get('total_memory_mb', 0)} MB",
        "Disk Free": f"{info.get('available_disk_mb', 0)} MB",
        "Termux": (
            "[cpip.success]Yes[/cpip.success]"
            if info.get("is_termux")
            else "[cpip.dim]No[/cpip.dim]"
        ),
        "GPU": (
            "[cpip.status.gpu]⚡ Detected[/cpip.status.gpu]"
            if info.get("has_gpu")
            else "[cpip.dim]None[/cpip.dim]"
        ),
    }
    return status_panel("System Information", status_items, border_style="cyan")


def cloud_status_panel(connected: bool, api_url: str, stats: dict[str, Any] | None = None) -> Panel:
    """Create a cloud status panel."""
    items = {
        "Status": (
            "[cpip.success]● Connected[/cpip.success]"
            if connected
            else "[cpip.error]● Disconnected[/cpip.error]"
        ),
        "API": f"[cpip.url]{api_url}[/cpip.url]",
    }
    if stats:
        items["Build Queue"] = str(stats.get("build_queue_size", 0))
        items["Active Exec"] = str(stats.get("active_executions", 0))
        items["Devices"] = str(stats.get("connected_devices", 0))
    return status_panel("Cloud Status", items, border_style="bright_magenta")


def package_info_panel(name: str, version: str, strategy: str, details: dict[str, Any] | None = None) -> Panel:
    """Create a package information panel."""
    strategy_colors = {
        "local_install": "cpip.status.local",
        "cloud_wheel": "cpip.status.cloud",
        "cloud_exec": "cpip.status.cloud",
        "cloud_build": "cpip.status.cloud",
        "hybrid": "cpip.status.gpu",
        "termux_pkg": "cpip.status.local",
    }
    style = strategy_colors.get(strategy, "cpip.info")

    items = {
        "Package": f"[cpip.package]{name}[/cpip.package]",
        "Version": f"[cpip.version]{version}[/cpip.version]",
        "Strategy": f"[{style}]{strategy}[/{style}]",
    }
    if details:
        if "size" in details:
            items["Size"] = details["size"]
        if "dependencies" in details:
            items["Dependencies"] = ", ".join(details["dependencies"][:5])
        if "gpu_required" in details:
            items["GPU"] = (
                "[cpip.status.gpu]Required[/cpip.status.gpu]"
                if details["gpu_required"]
                else "Not required"
            )

    return status_panel(f"📦 {name}", items, border_style="bright_cyan")


def gpu_status_panel(gpus: list[dict[str, Any]] | None = None) -> Panel:
    """Create a GPU status panel."""
    if not gpus:
        content = Align.center(
            Text("No local GPU detected\nCloud GPU available via cpip runtime", style="cpip.dim")
        )
        return Panel(
            content,
            title="[cpip.header]GPU Status[/cpip.header]",
            border_style="bright_red",
            padding=(1, 2),
        )

    table = Table(show_edge=False, box=None, padding=(0, 2))
    table.add_column("GPU", style="cpip.primary")
    table.add_column("Memory", style="cpip.version")
    table.add_column("Status", style="cpip.success")

    for gpu in gpus:
        table.add_row(
            gpu.get("name", "Unknown"),
            gpu.get("memory", "N/A"),
            gpu.get("status", "available"),
        )

    return Panel(
        table,
        title="[cpip.header]⚡ GPU Status[/cpip.header]",
        border_style="bright_red",
        padding=(1, 2),
    )


def packages_table(packages: list[dict[str, Any]]) -> Table:
    """Create a table of installed packages."""
    table = Table(
        show_header=True,
        header_style="cpip.table.header",
        border_style="cpip.divider",
        padding=(0, 1),
    )
    table.add_column("Package", style="cpip.package", min_width=20)
    table.add_column("Version", style="cpip.version", min_width=10)
    table.add_column("Strategy", min_width=14)
    table.add_column("Size", justify="right", min_width=8)

    strategy_icons = {
        "local_install": "📦 local",
        "cloud_wheel": "☁️  wheel",
        "cloud_exec": "☁️  exec",
        "hybrid": "⚡ hybrid",
        "termux_pkg": "📱 termux",
    }

    for pkg in packages:
        strategy = pkg.get("strategy", "local_install")
        table.add_row(
            pkg.get("name", "?"),
            pkg.get("version", "?"),
            strategy_icons.get(strategy, strategy),
            pkg.get("size", ""),
        )

    return table


def dashboard(system: dict[str, Any], cloud_connected: bool, api_url: str) -> None:
    """Render the full cpip runtime dashboard."""
    console = get_console()

    panels = Columns(
        [
            system_info_panel(system),
            cloud_status_panel(cloud_connected, api_url),
        ],
        equal=True,
        expand=True,
    )
    console.print()
    console.print(panels)
    console.print()
