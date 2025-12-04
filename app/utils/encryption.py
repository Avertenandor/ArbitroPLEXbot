"""Encryption utilities for PII data."""

import base64
import os

from cryptography.fernet import Fernet
from loguru import logger


class EncryptionService:
    """
    Encryption service for sensitive data.

    Uses Fernet (symmetric encryption) for PII protection.
    """

    def __init__(self, encryption_key: str | None = None) -> None:
        """
        Initialize encryption service.

        Args:
            encryption_key: Base64-encoded Fernet key
        """
        self.environment = os.getenv("ENVIRONMENT", "development")

        if encryption_key:
            try:
                self.fernet = Fernet(encryption_key.encode())
                self.enabled = True
            except Exception as e:
                logger.error(f"Invalid encryption key: {e}")
                self.fernet = None
                self.enabled = False
                if self.environment == "production":
                    from app.utils.exceptions import SecurityError
                    raise SecurityError(
                        "Invalid encryption key in production environment. "
                        "Encryption is required for security."
                    )
        else:
            self.fernet = None
            self.enabled = False
            if self.environment == "production":
                from app.utils.exceptions import SecurityError
                raise SecurityError(
                    "Encryption key not configured in production environment. "
                    "Set ENCRYPTION_KEY in .env file."
                )

    def encrypt(self, plaintext: str) -> str | None:
        """
        Encrypt plaintext.

        Args:
            plaintext: Text to encrypt

        Returns:
            Encrypted text (base64) or None if disabled
        """
        if not self.enabled:
            if self.environment == "production":
                from app.utils.exceptions import SecurityError
                raise SecurityError(
                    "Encryption must be enabled in production. "
                    "Cannot save sensitive data without encryption."
                )
            logger.warning("Encryption disabled - returning plaintext (DEV ONLY)")
            return plaintext

        if not self.fernet:
            from app.utils.exceptions import SecurityError
            raise SecurityError("Encryption key not configured")

        try:
            encrypted = self.fernet.encrypt(plaintext.encode())
            return base64.b64encode(encrypted).decode()

        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return None

    def decrypt(self, ciphertext: str) -> str | None:
        """
        Decrypt ciphertext.

        Args:
            ciphertext: Encrypted text (base64)

        Returns:
            Decrypted text or None if error
        """
        if not self.enabled:
            if self.environment == "production":
                from app.utils.exceptions import SecurityError
                raise SecurityError(
                    "Encryption must be enabled in production. "
                    "Cannot decrypt data without encryption service."
                )
            logger.warning("Encryption disabled - returning ciphertext as-is (DEV ONLY)")
            return ciphertext

        if not self.fernet:
            from app.utils.exceptions import SecurityError
            raise SecurityError("Encryption key not configured")

        try:
            encrypted = base64.b64decode(ciphertext.encode())
            decrypted = self.fernet.decrypt(encrypted)
            return decrypted.decode()

        except Exception as e:
            logger.error(f"Decryption error: {e}")
            from app.utils.exceptions import SecurityError
            raise SecurityError(f"Decryption failed: {e}")

    @staticmethod
    def generate_key() -> str:
        """
        Generate new Fernet key.

        Returns:
            Base64-encoded key
        """
        return Fernet.generate_key().decode()


# Singleton instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService | None:
    """Get encryption service singleton."""
    return _encryption_service


def init_encryption_service(
    encryption_key: str | None = None
) -> EncryptionService:
    """Initialize encryption service singleton."""
    global _encryption_service

    _encryption_service = EncryptionService(encryption_key)

    return _encryption_service
