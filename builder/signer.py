"""
Package signing with Ed25519.

Signs built wheels and verifies package integrity.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


class PackageSigner:
    """Signs and verifies packages with Ed25519."""

    def __init__(self, private_key: Ed25519PrivateKey | None = None, public_key: Ed25519PublicKey | None = None):
        self._private = private_key
        self._public = public_key

    @classmethod
    def generate(cls) -> PackageSigner:
        private = Ed25519PrivateKey.generate()
        return cls(private_key=private, public_key=private.public_key())

    @classmethod
    def from_key_file(cls, path: str) -> PackageSigner:
        data = Path(path).read_bytes()
        private = serialization.load_pem_private_key(data, password=None)
        return cls(private_key=private, public_key=private.public_key())  # type: ignore

    def sign_file(self, file_path: str) -> str:
        """Sign a file and return base64-encoded signature."""
        if not self._private:
            raise ValueError("No private key available")
        data = Path(file_path).read_bytes()
        signature = self._private.sign(data)
        return base64.b64encode(signature).decode("ascii")

    def verify_file(self, file_path: str, signature_b64: str) -> bool:
        """Verify a file's signature."""
        if not self._public:
            raise ValueError("No public key available")
        data = Path(file_path).read_bytes()
        signature = base64.b64decode(signature_b64)
        try:
            self._public.verify(signature, data)
            return True
        except Exception:
            return False

    def export_public_key(self) -> str:
        if not self._public:
            raise ValueError("No public key")
        return self._public.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

    def export_private_key(self) -> str:
        if not self._private:
            raise ValueError("No private key")
        return self._private.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        ).decode()
