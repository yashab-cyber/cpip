"""
Audit logging for security events.

Records sensitive actions, authentication failures, and execution attempts.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from shared.constants import LOG_DIR


class AuditLogger:
    """Logs security-relevant events."""

    def __init__(self, log_dir: str = LOG_DIR):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "audit.jsonl"
        
        # Setup standard Python logging as well
        self.logger = logging.getLogger("cpip.audit")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(self.log_dir / "audit.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_event(self, event_type: str, user_id: str, device_id: str, details: dict) -> None:
        """Log a structured security event."""
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "user_id": user_id,
            "device_id": device_id,
            "details": details
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
            self.logger.info(f"Audit event: {event_type} | User: {user_id} | Device: {device_id} | Details: {json.dumps(details)}")
        except Exception:
            pass

    def log_auth_success(self, user_id: str, device_id: str, ip_address: str = "") -> None:
        self.log_event("auth_success", user_id, device_id, {"ip_address": ip_address})

    def log_auth_failure(self, user_id: str, device_id: str, reason: str, ip_address: str = "") -> None:
        self.log_event("auth_failure", user_id, device_id, {"reason": reason, "ip_address": ip_address})

    def log_execution(self, user_id: str, device_id: str, method: str, sandbox_config: dict) -> None:
        self.log_event("execution_attempt", user_id, device_id, {"method": method, "sandbox": sandbox_config})

    def log_package_install(self, user_id: str, device_id: str, package: str, strategy: str) -> None:
        self.log_event("package_install", user_id, device_id, {"package": package, "strategy": strategy})


audit_logger = AuditLogger()
