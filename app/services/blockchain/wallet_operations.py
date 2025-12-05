"""
Wallet operations for blockchain service.

This module handles:
- Wallet initialization from encrypted private keys
- Address validation
- Secure key management
"""

from eth_account import Account
from eth_utils import is_address, to_checksum_address
from loguru import logger

from app.config.settings import Settings
from app.utils.encryption import get_encryption_service
from app.utils.exceptions import SecurityError

from .security_utils import secure_zero_memory


class WalletManager:
    """
    Manages wallet operations including initialization and validation.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize wallet manager.

        Args:
            settings: Application settings containing wallet configuration
        """
        self.settings = settings
        self.wallet_private_key = settings.wallet_private_key
        self.wallet_account = None
        self.wallet_address = None

        # Initialize wallet if private key is configured
        if self.wallet_private_key:
            self._init_wallet()

    def _init_wallet(self) -> None:
        """
        Initialize wallet account.

        SECURITY: Automatically decrypts private key if it was encrypted.
        Private key is kept in memory only for signing - cleared immediately after use.
        """
        private_key = None
        try:
            # CRITICAL: Decrypt private key if it's encrypted
            private_key = self.wallet_private_key
            encryption_service = get_encryption_service()

            if not encryption_service or not encryption_service.enabled:
                raise SecurityError(
                    "EncryptionService not available or disabled. "
                    "Cannot decrypt private key without encryption. "
                    "Ensure ENCRYPTION_KEY is set correctly."
                )

            # Try to decrypt - raises SecurityError on failure
            decrypted = encryption_service.decrypt(private_key)
            if not decrypted:
                raise SecurityError(
                    "Failed to decrypt private key. "
                    "Ensure ENCRYPTION_KEY is set correctly and key is encrypted."
                )

            private_key = decrypted
            logger.info("Private key decrypted successfully")

            # Initialize wallet account with decrypted key
            self.wallet_account = Account.from_key(private_key)
            self.wallet_address = to_checksum_address(self.wallet_account.address)

        except SecurityError:
            # Re-raise security errors without catching
            raise
        except Exception as e:
            logger.error(f"Failed to init wallet: {e}")
            self.wallet_account = None
            self.wallet_address = None
        finally:
            # SECURITY: Clear decrypted private key from memory
            if private_key and private_key != self.wallet_private_key:
                secure_zero_memory(private_key)
                del private_key

    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate wallet address format.

        Args:
            address: Wallet address to validate

        Returns:
            True if address is valid, False otherwise
        """
        try:
            return is_address(address)
        except (ValueError, TypeError) as e:
            logger.debug(f"Invalid wallet address format: {e}")
            return False

    def cleanup(self) -> None:
        """
        Clean up sensitive wallet data.

        SECURITY: Clear sensitive data on shutdown
        """
        if self.wallet_private_key:
            secure_zero_memory(self.wallet_private_key)
        if self.wallet_account:
            self.wallet_account = None
