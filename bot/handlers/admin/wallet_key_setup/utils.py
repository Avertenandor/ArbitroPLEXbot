"""
Wallet Setup Utility Functions.

Provides helper functions for secure memory handling and environment variable updates.
"""

import ctypes
import os

from loguru import logger

from app.utils.encryption import get_encryption_service


def secure_zero_memory(secret: str) -> None:
    """
    Securely overwrite memory containing secret data.

    NOTE: This provides best-effort memory clearing in Python.
    Python's memory management makes true secure erasure impossible,
    but this reduces the window of exposure.
    """
    if not secret:
        return

    try:
        # Convert to bytes if string
        secret_bytes = secret.encode() if isinstance(secret, str) else secret
        # Overwrite with zeros
        ctypes.memset(id(secret_bytes) + 32, 0, len(secret_bytes))
    except Exception as e:
        # Fail silently - this is best-effort security
        logger.debug(f"Memory zeroing failed: {type(e).__name__}")


def update_env_variable(key: str, value: str) -> None:
    """
    Update environment variable in .env file.

    SECURITY: Automatically encrypts private keys before saving.
    Raises exception if encryption fails - no fallback to plaintext.
    """
    env_file = "/app/.env"

    if not os.path.exists(env_file):
        # Try local path if container path fails (for dev)
        env_file = ".env"

    # CRITICAL: Encrypt private keys before saving to .env
    if key == "wallet_private_key":
        encryption_service = get_encryption_service()

        # SECURITY: Encryption is REQUIRED for private keys
        if not encryption_service or not encryption_service.enabled:
            raise ValueError(
                "CRITICAL SECURITY ERROR: EncryptionService not available. "
                "Cannot save private key without encryption. "
                "Configure encryption or contact system administrator."
            )

        encrypted_value = encryption_service.encrypt(value)
        if not encrypted_value:
            raise ValueError(
                "CRITICAL SECURITY ERROR: Failed to encrypt private key. "
                "Cannot save private key without encryption. "
                "Check encryption service logs or contact system administrator."
            )

        value = encrypted_value
        logger.info("Private key encrypted successfully before saving to .env")

    try:
        with open(env_file, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    new_lines = []
    updated = False

    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines.append('\n')
        new_lines.append(f"{key}={value}\n")

    # Write directly to file to avoid "Device or resource busy" with Docker bind mounts
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
