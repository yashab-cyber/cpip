"""
Package signature verification.

Verifies the Ed25519 signatures of downloaded wheels to ensure
they have not been tampered with.
"""

from __future__ import annotations

import base64
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


class SignatureVerifier:
    """Verifies package signatures against trusted keys."""

    def __init__(self):
        self._trusted_keys: dict[str, Ed25519PublicKey] = {}

    def load_public_key(self, key_id: str, pem_data: str) -> None:
        key = serialization.load_pem_public_key(pem_data.encode("utf-8"))
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("Must be an Ed25519 public key")
        self._trusted_keys[key_id] = key

    def verify_file(self, file_path: str, signature_b64: str, key_id: str | None = None) -> bool:
        """Verify a file's signature."""
        if not self._trusted_keys:
            return False

        data = Path(file_path).read_bytes()
        signature = base64.b64decode(signature_b64)

        keys_to_try = [self._trusted_keys[key_id]] if key_id and key_id in self._trusted_keys else self._trusted_keys.values()

        for key in keys_to_try:
            try:
                key.verify(signature, data)
                return True
            except Exception:
                pass
        return False


verifier = SignatureVerifier()
