"""
Agent tool definitions.

Provides tool interfaces for AI agents to interact with cpip runtime.
"""

from __future__ import annotations

from typing import Any


class CpipTools:
    """Tool definitions for AI agent integration."""

    @staticmethod
    async def install_package(package: str, version: str = "latest") -> dict:
        from client.config import load_config
        from client.cache import CacheManager
        from client.resolver import PackageResolver
        from client.installer import PackageInstaller

        config = load_config()
        cache = CacheManager(config.cache.max_size_mb)
        resolver = PackageResolver(config, cache)
        installer = PackageInstaller(config, cache, resolver)
        try:
            success = await installer.install(package, version)
            await resolver.close()
            return {"success": success, "package": package}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def execute_code(code: str, gpu: bool = False) -> dict:
        from executor.sandbox import sandbox, SandboxConfig
        config = SandboxConfig(gpu=gpu)
        result = await sandbox.execute(code, config)
        return {"success": result.success, "output": result.stdout, "error": result.stderr}

    @staticmethod
    async def browse_url(url: str) -> dict:
        from agent.browser import browser_agent
        return await browser_agent.navigate(url)

    @staticmethod
    async def screenshot_url(url: str) -> dict:
        from agent.browser import browser_agent
        return await browser_agent.screenshot(url)

    @staticmethod
    async def run_model(model: str, input_data: Any) -> dict:
        from agent.router import model_router
        target = model_router.route(model)
        return {"model": model, "target": target, "status": "routed"}

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        """Return OpenAI-compatible tool definitions."""
        return [
            {"type": "function", "function": {"name": "cpip_install", "description": "Install a Python package via cpip", "parameters": {"type": "object", "properties": {"package": {"type": "string"}, "version": {"type": "string", "default": "latest"}}, "required": ["package"]}}},
            {"type": "function", "function": {"name": "cpip_execute", "description": "Execute Python code in cloud sandbox", "parameters": {"type": "object", "properties": {"code": {"type": "string"}, "gpu": {"type": "boolean", "default": False}}, "required": ["code"]}}},
            {"type": "function", "function": {"name": "cpip_browse", "description": "Navigate to URL and get page content", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
            {"type": "function", "function": {"name": "cpip_screenshot", "description": "Take screenshot of a URL", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
        ]


tools = CpipTools()
