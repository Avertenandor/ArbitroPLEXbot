"""
Secure Redis Storage for sensitive data.

Provides encryption/decryption for passwords and other secrets stored in Redis.
"""

from typing import Any

from loguru import logger
from redis.asyncio import Redis

from app.utils.encryption import get_encryption_service


class SecureRedisStorage:
    """
    Secure Redis storage with automatic encryption/decryption.

    Uses EncryptionService for encrypting sensitive data before storage.
    """

    def __init__(self, redis_client: Redis) -> None:
        """
        Initialize secure storage.

        Args:
            redis_client: Async Redis client
        """
        self.redis = redis_client
        self.encryption = get_encryption_service()

        if not self.encryption or not self.encryption.enabled:
            logger.warning(
                "SecureRedisStorage: Encryption service not enabled! "
                "Data will be stored without encryption."
            )

    async def set_secret(
        self, key: str, value: str, ttl: int = 3600
    ) -> bool:
        """
        Store encrypted secret in Redis.

        Args:
            key: Redis key
            value: Plain text value to encrypt and store
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Encrypt value
            if self.encryption and self.encryption.enabled:
                encrypted = self.encryption.encrypt(value)
                if not encrypted:
                    logger.error(
                        f"Failed to encrypt secret for key: {key}"
                    )
                    return False
            else:
                # Fallback: store without encryption if service disabled
                encrypted = value
                logger.warning(
                    f"Storing secret without encryption for key: {key}"
                )

            # Store in Redis
            await self.redis.setex(key, ttl, encrypted)
            logger.debug(f"Secret stored securely for key: {key}")
            return True

        except Exception as e:
            logger.error(
                f"Error storing secret for key {key}: {e}",
                exc_info=True,
            )
            return False

    async def get_secret(self, key: str) -> str | None:
        """
        Retrieve and decrypt secret from Redis.

        Args:
            key: Redis key

        Returns:
            Decrypted value or None if not found/error
        """
        try:
            # Get from Redis
            encrypted = await self.redis.get(key)

            if not encrypted:
                return None

            # Decode if bytes
            if isinstance(encrypted, bytes):
                encrypted = encrypted.decode("utf-8")

            # Decrypt value
            if self.encryption and self.encryption.enabled:
                decrypted = self.encryption.decrypt(encrypted)
                if not decrypted:
                    logger.error(
                        f"Failed to decrypt secret for key: {key}"
                    )
                    return None
                return decrypted
            else:
                # Fallback: return as-is if service disabled
                logger.warning(
                    f"Retrieving secret without decryption for key: {key}"
                )
                return encrypted

        except Exception as e:
            logger.error(
                f"Error retrieving secret for key {key}: {e}",
                exc_info=True,
            )
            return None

    async def delete_secret(self, key: str) -> bool:
        """
        Delete secret from Redis.

        Args:
            key: Redis key

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(
                f"Error deleting secret for key {key}: {e}",
                exc_info=True,
            )
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if secret exists in Redis.

        Args:
            key: Redis key

        Returns:
            True if exists, False otherwise
        """
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(
                f"Error checking secret existence for key {key}: {e}",
                exc_info=True,
            )
            return False
