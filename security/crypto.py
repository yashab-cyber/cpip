"""
Cryptography utilities.

Provides AES-256-GCM encryption for sensitive data and
Argon2 key derivation.
"""

from __future__ import annotations

import base64
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoManager:
    """Manages encryption and decryption of sensitive data."""

    def __init__(self, master_key: bytes | None = None):
        if master_key and len(master_key) != 32:
            raise ValueError("Master key must be exactly 32 bytes")
        self._key = master_key or os.urandom(32)
        self._aesgcm = AESGCM(self._key)

    @classmethod
    def generate_key(cls) -> bytes:
        return os.urandom(32)

    def encrypt(self, data: bytes) -> str:
        """Encrypt data using AES-256-GCM. Returns base64 encoded string."""
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, data, None)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, encrypted_b64: str) -> bytes:
        """Decrypt a base64 encoded string back to bytes."""
        raw = base64.b64decode(encrypted_b64)
        if len(raw) < 12:
            raise ValueError("Invalid encrypted data length")
        nonce = raw[:12]
        ciphertext = raw[12:]
        return self._aesgcm.decrypt(nonce, ciphertext, None)


crypto_manager = CryptoManager()
