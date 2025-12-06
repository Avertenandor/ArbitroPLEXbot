"""
Balance operations for blockchain tokens.

This module handles:
- USDT balance checking
- PLEX token balance checking
- Native BNB balance checking
"""

from decimal import Decimal

from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3

from app.utils.security import mask_address

from .core_constants import PLEX_ABI, PLEX_DECIMALS, USDT_ABI, USDT_DECIMALS


class BalanceManager:
    """
    Manages balance checking operations for various tokens.
    """

    def __init__(self, usdt_contract_address: str, plex_token_address: str | None = None) -> None:
        """
        Initialize balance manager.

        Args:
            usdt_contract_address: USDT contract address
            plex_token_address: PLEX token contract address (optional)
        """
        self.usdt_contract_address = to_checksum_address(usdt_contract_address)
        self.plex_token_address = (
            to_checksum_address(plex_token_address) if plex_token_address else None
        )

    async def get_usdt_balance(self, w3: Web3, address: str) -> Decimal | None:
        """
        Get USDT balance for address.

        Args:
            w3: Web3 instance
            address: Wallet address to check

        Returns:
            USDT balance in tokens or None on error
        """
        try:
            address = to_checksum_address(address)
            contract = w3.eth.contract(address=self.usdt_contract_address, abi=USDT_ABI)
            wei = contract.functions.balanceOf(address).call()
            return Decimal(wei) / Decimal(10 ** USDT_DECIMALS)
        except Exception as e:
            logger.error(f"Get USDT balance failed: {e}")
            return None

    async def get_plex_balance(self, w3: Web3, address: str) -> Decimal | None:
        """
        Get PLEX token balance for address.

        PLEX token uses 9 decimals (per business rules).

        Args:
            w3: Web3 instance
            address: Wallet address to check

        Returns:
            PLEX balance in tokens or None on error
        """
        if not self.plex_token_address:
            logger.error("PLEX token address not configured")
            return None

        try:
            address = to_checksum_address(address)
            # PLEX uses standard ERC-20 ABI
            contract = w3.eth.contract(address=self.plex_token_address, abi=PLEX_ABI)
            raw = contract.functions.balanceOf(address).call()
            # PLEX has 9 decimals
            return Decimal(raw) / Decimal(10**PLEX_DECIMALS)
        except Exception as e:
            logger.error(f"Get PLEX balance failed for {mask_address(address)}: {e}")
            return None

    async def get_native_balance(self, w3: Web3, address: str) -> Decimal | None:
        """
        Get Native Token (BNB) balance for address.

        Args:
            w3: Web3 instance
            address: Wallet address to check

        Returns:
            BNB balance in tokens or None on error
        """
        try:
            address = to_checksum_address(address)
            wei = w3.eth.get_balance(address)
            return Decimal(wei) / Decimal(10 ** 18)
        except Exception as e:
            logger.error(f"Get BNB balance failed: {e}")
            return None
