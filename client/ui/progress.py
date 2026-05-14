"""
Custom progress bars and download indicators.

Provides beautiful, informative progress bars for package downloads,
builds, and cloud operations.
"""

from __future__ import annotations

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from client.ui.console import get_console


def download_progress() -> Progress:
    """Create a progress bar for file downloads."""
    return Progress(
        SpinnerColumn("dots", style="cpip.primary"),
        TextColumn("[cpip.package]{task.fields[package]}[/cpip.package]"),
        BarColumn(
            bar_width=30,
            style="cpip.divider",
            complete_style="cpip.primary",
            finished_style="cpip.success",
        ),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=get_console(),
        expand=False,
    )


def build_progress() -> Progress:
    """Create a progress bar for cloud builds."""
    return Progress(
        SpinnerColumn("bouncingBall", style="cpip.status.cloud"),
        TextColumn("[cpip.status.cloud]☁[/cpip.status.cloud]"),
        TextColumn("[cpip.package]{task.fields[package]}[/cpip.package]"),
        TextColumn("[cpip.dim]{task.fields[stage]}[/cpip.dim]"),
        BarColumn(
            bar_width=25,
            style="cpip.divider",
            complete_style="cpip.status.cloud",
            finished_style="cpip.success",
        ),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=get_console(),
        expand=False,
    )


def install_progress() -> Progress:
    """Create a progress bar for package installation."""
    return Progress(
        SpinnerColumn("arc", style="cpip.primary"),
        TextColumn("[cpip.primary]installing[/cpip.primary]"),
        TextColumn("[cpip.package]{task.fields[package]}[/cpip.package]"),
        BarColumn(
            bar_width=30,
            style="cpip.divider",
            complete_style="cpip.primary",
            finished_style="cpip.success",
        ),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=get_console(),
        expand=False,
    )


def sync_progress() -> Progress:
    """Create a progress bar for sync operations."""
    return Progress(
        SpinnerColumn("dots12", style="cpip.info"),
        TextColumn("[cpip.info]syncing[/cpip.info]"),
        TextColumn("{task.description}"),
        BarColumn(
            bar_width=25,
            style="cpip.divider",
            complete_style="cpip.info",
            finished_style="cpip.success",
        ),
        TaskProgressColumn(),
        console=get_console(),
        expand=False,
    )


def exec_spinner(message: str = "Processing...") -> Progress:
    """Create a spinner for cloud execution operations."""
    return Progress(
        SpinnerColumn("dots2", style="cpip.status.gpu"),
        TextColumn(f"[cpip.status.gpu]⚡[/cpip.status.gpu] {message}"),
        TimeElapsedColumn(),
        console=get_console(),
        expand=False,
    )


def multi_package_progress() -> Progress:
    """Create a progress bar for multi-package operations."""
    return Progress(
        SpinnerColumn("dots", style="cpip.primary"),
        TextColumn("{task.description}"),
        BarColumn(
            bar_width=35,
            style="cpip.divider",
            complete_style="cpip.primary",
            finished_style="cpip.success",
        ),
        TextColumn("[cpip.dim]{task.fields[status]}[/cpip.dim]"),
        TaskProgressColumn(),
        console=get_console(),
        expand=False,
    )
