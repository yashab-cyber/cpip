"""
Rich console theming and singleton.

Provides a unified, beautiful console experience with cpip branding,
custom themes, and styled output helpers.
"""

from __future__ import annotations

from rich.console import Console
from rich.style import Style
from rich.theme import Theme

# ── cpip Color Palette ───────────────────────────────────────────────
# Inspired by cyberpunk / futuristic AI aesthetics
CPIP_THEME = Theme(
    {
        # Primary colors
        "cpip.primary": Style(color="#00D4FF", bold=True),
        "cpip.secondary": Style(color="#7B61FF"),
        "cpip.accent": Style(color="#FF6B6B"),
        "cpip.success": Style(color="#00E676", bold=True),
        "cpip.warning": Style(color="#FFD600", bold=True),
        "cpip.error": Style(color="#FF1744", bold=True),
        "cpip.info": Style(color="#448AFF"),
        "cpip.dim": Style(color="#78909C"),
        "cpip.muted": Style(color="#546E7A", dim=True),

        # Semantic styles
        "cpip.package": Style(color="#00D4FF", bold=True),
        "cpip.version": Style(color="#7B61FF"),
        "cpip.strategy": Style(color="#FF6B6B", italic=True),
        "cpip.path": Style(color="#80CBC4"),
        "cpip.url": Style(color="#448AFF", underline=True),
        "cpip.command": Style(color="#FFD600", bold=True),

        # Status indicators
        "cpip.status.ok": Style(color="#00E676"),
        "cpip.status.warn": Style(color="#FFD600"),
        "cpip.status.fail": Style(color="#FF1744"),
        "cpip.status.cloud": Style(color="#7B61FF"),
        "cpip.status.local": Style(color="#00D4FF"),
        "cpip.status.gpu": Style(color="#FF6B6B"),

        # Progress & spinners
        "cpip.progress.bar": Style(color="#00D4FF"),
        "cpip.progress.text": Style(color="#B0BEC5"),
        "cpip.progress.speed": Style(color="#7B61FF"),

        # Headers and sections
        "cpip.header": Style(color="#00D4FF", bold=True),
        "cpip.subheader": Style(color="#B0BEC5", bold=True),
        "cpip.divider": Style(color="#37474F"),

        # Table
        "cpip.table.header": Style(color="#00D4FF", bold=True),
        "cpip.table.row": Style(color="#ECEFF1"),
        "cpip.table.row.alt": Style(color="#B0BEC5"),
    }
)


# ── Console Singleton ────────────────────────────────────────────────

_console: Console | None = None


def get_console() -> Console:
    """Get the global Rich console with cpip theme."""
    global _console
    if _console is None:
        _console = Console(theme=CPIP_THEME, highlight=False)
    return _console


# ── Styled Output Helpers ────────────────────────────────────────────

def print_banner() -> None:
    """Print the cpip startup banner."""
    from shared.constants import BANNER, CODENAME, VERSION

    console = get_console()
    banner_text = BANNER.format(version=VERSION, codename=CODENAME)
    console.print(banner_text)


def print_success(message: str) -> None:
    """Print a success message."""
    get_console().print(f"  [cpip.success]✓[/cpip.success] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    get_console().print(f"  [cpip.error]✗[/cpip.error] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    get_console().print(f"  [cpip.warning]⚠[/cpip.warning] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    get_console().print(f"  [cpip.info]ℹ[/cpip.info] {message}")


def print_cloud(message: str) -> None:
    """Print a cloud-related message."""
    get_console().print(f"  [cpip.status.cloud]☁[/cpip.status.cloud] {message}")


def print_gpu(message: str) -> None:
    """Print a GPU-related message."""
    get_console().print(f"  [cpip.status.gpu]⚡[/cpip.status.gpu] {message}")


def print_package(name: str, version: str = "", strategy: str = "") -> None:
    """Print a package info line."""
    console = get_console()
    parts = [f"  [cpip.package]{name}[/cpip.package]"]
    if version:
        parts.append(f"[cpip.version]{version}[/cpip.version]")
    if strategy:
        parts.append(f"[cpip.strategy]({strategy})[/cpip.strategy]")
    console.print(" ".join(parts))


def print_divider(title: str = "") -> None:
    """Print a section divider."""
    console = get_console()
    if title:
        console.print(f"\n  [cpip.header]━━━ {title} ━━━[/cpip.header]")
    else:
        console.print("  [cpip.divider]" + "━" * 50 + "[/cpip.divider]")


def print_step(step: int, total: int, message: str) -> None:
    """Print a numbered step."""
    get_console().print(
        f"  [cpip.dim][{step}/{total}][/cpip.dim] {message}"
    )
