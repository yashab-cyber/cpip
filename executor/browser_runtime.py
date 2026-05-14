"""Browser automation runtime using Playwright in cloud containers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from executor.sandbox import Sandbox, SandboxConfig, SandboxResult


class BrowserRuntime:
    """Manages Playwright/Chromium execution in cloud."""

    def __init__(self):
        self._sandbox = Sandbox()
        self._image = "mcr.microsoft.com/playwright/python:latest"

    async def run_playwright(self, script: str) -> SandboxResult:
        config = SandboxConfig(
            image=self._image, network=True, memory_limit="4g", timeout=120,
        )
        return await self._sandbox.execute(script, config)

    async def screenshot(self, url: str) -> SandboxResult:
        code = f"""
from playwright.sync_api import sync_playwright
import base64
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("{url}")
    screenshot = page.screenshot()
    print(base64.b64encode(screenshot).decode())
    browser.close()
"""
        return await self.run_playwright(code)

    async def get_html(self, url: str) -> SandboxResult:
        code = f"""
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("{url}")
    print(page.content())
    browser.close()
"""
        return await self.run_playwright(code)


browser_runtime = BrowserRuntime()
