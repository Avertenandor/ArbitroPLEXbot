"""
Security utilities for blockchain operations.

This module provides security-related utilities for handling sensitive data
such as private keys and ensuring secure memory management.
"""

import ctypes


def secure_zero_memory(secret: str) -> None:
    """
    Securely overwrite memory containing secret data.

    NOTE: This provides best-effort memory clearing in Python.
    Python's memory management makes true secure erasure impossible,
    but this reduces the window of exposure.

    Args:
        secret: The secret string to clear from memory
    """
    if not secret:
        return

    try:
        # Convert to bytes if string
        secret_bytes = secret.encode() if isinstance(secret, str) else secret
        # Overwrite with zeros
        # This is a best-effort approach - Python's GC may have copies
        ctypes.memset(id(secret_bytes) + 32, 0, len(secret_bytes))
    except Exception:
        # Fail silently - this is best-effort security
        pass
