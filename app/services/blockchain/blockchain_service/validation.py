"""
Validation Module.

Contains validation utilities for the BlockchainService.
"""

from app.validators.unified import validate_wallet_address as _validate_wallet_address


class Validation:
    """
    Handles validation operations.

    Features:
    - Wallet address validation
    """

    @staticmethod
    async def validate_wallet_address(address: str) -> bool:
        """
        Validate BSC wallet address format.

        Args:
            address: Wallet address

        Returns:
            True if valid
        """
        # Use unified validator
        is_valid, _ = _validate_wallet_address(address)
        return is_valid
