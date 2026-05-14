"""
cpip exception hierarchy.

All cpip-specific exceptions inherit from CpipError for
easy catch-all handling. Each subsystem has its own category.
"""

from __future__ import annotations


class CpipError(Exception):
    """Base exception for all cpip errors."""

    def __init__(self, message: str = "", code: str = "CPIP_ERROR", details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


# ── Cloud / Network ──────────────────────────────────────────────────

class CloudUnavailableError(CpipError):
    """Cloud backend is unreachable."""

    def __init__(self, message: str = "Cloud service is unavailable"):
        super().__init__(message, code="CLOUD_UNAVAILABLE")


class ConnectionTimeoutError(CpipError):
    """WebSocket or HTTP connection timed out."""

    def __init__(self, message: str = "Connection timed out"):
        super().__init__(message, code="CONNECTION_TIMEOUT")


class WebSocketError(CpipError):
    """WebSocket communication error."""

    def __init__(self, message: str = "WebSocket error"):
        super().__init__(message, code="WEBSOCKET_ERROR")


# ── Packages ─────────────────────────────────────────────────────────

class PackageNotFoundError(CpipError):
    """Requested package does not exist in any registry."""

    def __init__(self, package: str):
        super().__init__(
            f"Package '{package}' not found in any registry",
            code="PACKAGE_NOT_FOUND",
            details={"package": package},
        )


class PackageInstallError(CpipError):
    """Package installation failed."""

    def __init__(self, package: str, reason: str = ""):
        super().__init__(
            f"Failed to install '{package}': {reason}",
            code="PACKAGE_INSTALL_FAILED",
            details={"package": package, "reason": reason},
        )


class PackageIntegrityError(CpipError):
    """Package integrity check failed (hash mismatch, invalid signature)."""

    def __init__(self, package: str, reason: str = ""):
        super().__init__(
            f"Integrity check failed for '{package}': {reason}",
            code="PACKAGE_INTEGRITY_FAILED",
            details={"package": package, "reason": reason},
        )


# ── Build ────────────────────────────────────────────────────────────

class BuildError(CpipError):
    """Cloud build failed."""

    def __init__(self, package: str, reason: str = ""):
        super().__init__(
            f"Build failed for '{package}': {reason}",
            code="BUILD_FAILED",
            details={"package": package, "reason": reason},
        )


class BuildTimeoutError(BuildError):
    """Build exceeded time limit."""

    def __init__(self, package: str):
        super().__init__(package, reason="Build timed out")
        self.code = "BUILD_TIMEOUT"


class BuildQueueFullError(BuildError):
    """Build queue is at capacity."""

    def __init__(self):
        CpipError.__init__(self, "Build queue is full, try again later", code="BUILD_QUEUE_FULL")


# ── Execution ────────────────────────────────────────────────────────

class ExecutionError(CpipError):
    """Remote execution failed."""

    def __init__(self, message: str = "Remote execution failed", details: dict | None = None):
        super().__init__(message, code="EXECUTION_FAILED", details=details)


class ExecutionTimeoutError(ExecutionError):
    """Remote execution exceeded time limit."""

    def __init__(self, timeout: int = 0):
        super().__init__(
            f"Execution timed out after {timeout}s",
            details={"timeout": timeout},
        )
        self.code = "EXECUTION_TIMEOUT"


class SerializationError(CpipError):
    """Failed to serialize/deserialize execution data."""

    def __init__(self, message: str = "Serialization error"):
        super().__init__(message, code="SERIALIZATION_ERROR")


# ── Authentication ───────────────────────────────────────────────────

class AuthenticationError(CpipError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTH_FAILED")


class TokenExpiredError(AuthenticationError):
    """JWT token has expired."""

    def __init__(self):
        CpipError.__init__(self, "Token has expired", code="TOKEN_EXPIRED")


class RateLimitError(CpipError):
    """API rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded, retry after {retry_after}s",
            code="RATE_LIMITED",
            details={"retry_after": retry_after},
        )


# ── Security ─────────────────────────────────────────────────────────

class SecurityError(CpipError):
    """Security violation detected."""

    def __init__(self, message: str = "Security violation"):
        super().__init__(message, code="SECURITY_ERROR")


class SandboxViolationError(SecurityError):
    """Sandbox escape or policy violation."""

    def __init__(self, message: str = "Sandbox policy violation"):
        CpipError.__init__(self, message, code="SANDBOX_VIOLATION")


# ── Platform ─────────────────────────────────────────────────────────

class PlatformError(CpipError):
    """Platform or architecture is not supported."""

    def __init__(self, message: str = "Unsupported platform"):
        super().__init__(message, code="PLATFORM_ERROR")


class DaemonNotRunningError(CpipError):
    """cpip daemon is not running."""

    def __init__(self):
        super().__init__("cpip daemon is not running. Start it with: cpip daemon start", code="DAEMON_NOT_RUNNING")
