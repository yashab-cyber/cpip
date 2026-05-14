"""
Build worker — processes build jobs from the queue.

Pulls jobs, runs cross-compilation, signs artifacts, scans for security,
and publishes results.
"""

from __future__ import annotations

import asyncio
import logging
import time

from builder.compiler import compiler, CompileResult
from builder.queue import build_queue
from builder.scanner import scanner
from builder.signer import PackageSigner
from shared.models import BuildResult, BuildStatus

logger = logging.getLogger("cpip.builder")


class BuildWorker:
    """Processes build jobs from the queue."""

    def __init__(self, signer: PackageSigner | None = None):
        self.signer = signer or PackageSigner.generate()
        self._running = False

    async def start(self, poll_interval: float = 5) -> None:
        self._running = True
        logger.info("Build worker started")
        while self._running:
            req = build_queue.pop()
            if req:
                await self._process_build(req)
            else:
                await asyncio.sleep(poll_interval)

    async def stop(self) -> None:
        self._running = False

    async def _process_build(self, req) -> None:
        logger.info(f"Building {req.package_name} {req.package_version}")
        try:
            result = await compiler.compile(
                req.package_name, req.package_version,
                req.python_version, req.target_architecture,
            )

            if result.success and result.wheel_path:
                # Scan
                scan = await scanner.scan_wheel(result.wheel_path)
                if not scan.clean:
                    logger.warning(f"Security issues: {scan.issues}")
                    build_queue.fail(req.request_id)
                    return

                # Sign
                signature = self.signer.sign_file(result.wheel_path)
                logger.info(f"Built and signed: {result.wheel_path}")
                build_queue.complete(req.request_id)
            else:
                logger.error(f"Build failed: {result.error}")
                build_queue.fail(req.request_id)
        except Exception as e:
            logger.error(f"Build error: {e}")
            build_queue.fail(req.request_id)


async def run_worker():
    worker = BuildWorker()
    await worker.start()
