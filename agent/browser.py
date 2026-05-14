"""
Browser automation support for AI agents.

Provides Playwright session management via cloud execution,
enabling browser automation from Termux without local Chromium.
"""

from __future__ import annotations

from typing import Any

from executor.browser_runtime import browser_runtime


class BrowserAgent:
    """Browser automation interface for AI agents."""

    async def navigate(self, url: str) -> dict:
        result = await browser_runtime.get_html(url)
        return {"success": result.success, "html": result.stdout[:10000] if result.success else "", "error": result.stderr}

    async def screenshot(self, url: str) -> dict:
        result = await browser_runtime.screenshot(url)
        return {"success": result.success, "screenshot_b64": result.stdout if result.success else "", "error": result.stderr}

    async def execute_script(self, script: str) -> dict:
        result = await browser_runtime.run_playwright(script)
        return {"success": result.success, "output": result.stdout, "error": result.stderr}

    async def fill_form(self, url: str, fields: dict[str, str]) -> dict:
        field_code = "\n".join(f'    page.fill("{sel}", "{val}")' for sel, val in fields.items())
        script = f"""
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("{url}")
{field_code}
    print("Form filled")
    browser.close()
"""
        result = await browser_runtime.run_playwright(script)
        return {"success": result.success, "output": result.stdout, "error": result.stderr}


browser_agent = BrowserAgent()
