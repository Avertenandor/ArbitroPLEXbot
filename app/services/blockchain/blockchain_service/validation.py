"""
Validation Module.

Contains validation utilities for the BlockchainService.
"""


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
        if not address or not isinstance(address, str):
            return False

        if not address.startswith("0x"):
            return False

        if len(address) != 42:  # 0x + 40 hex chars
            return False

        # Check if all chars after 0x are hex
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False
