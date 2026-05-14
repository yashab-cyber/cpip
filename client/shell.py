"""
Interactive cpip shell.

Enhanced Python REPL with cpip runtime hooks active,
cloud execution support, and Rich-powered output.
"""

from __future__ import annotations

import code
import sys

from client.config import CpipConfig
from client.ui.console import get_console, print_banner, print_info


class CpipShell:
    """Interactive Python shell with cpip runtime active."""

    def __init__(self, config: CpipConfig):
        self.config = config

    def start(self) -> None:
        """Launch the interactive shell."""
        console = get_console()
        print_banner()
        print_info("cpip runtime active — cloud packages available transparently")
        print_info("Type 'exit()' or Ctrl+D to quit\n")

        # Activate import hooks
        from runtime.hooks import activate_hooks
        activate_hooks(self.config)

        # Build shell namespace
        namespace = {
            "__name__": "__main__",
            "__doc__": None,
            "cpip_config": self.config,
        }

        # Start interactive console
        banner = ""
        try:
            shell = code.InteractiveConsole(locals=namespace)
            shell.interact(banner=banner, exitmsg="[cpip] Session ended.")
        except SystemExit:
            pass
