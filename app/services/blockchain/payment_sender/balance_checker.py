"""
Balance Checker for Payment Sender.

Provides functionality to query USDT and BNB balances.
"""

import asyncio
from decimal import Decimal

from loguru import logger
from web3 import AsyncWeb3
from web3.contract import AsyncContract

from app.config.constants import BLOCKCHAIN_TIMEOUT
from app.utils.security import mask_address

from ..constants import USDT_DECIMALS


class BalanceChecker:
    """
    Checks wallet balances for USDT and BNB.

    Features:
    - USDT balance queries
    - BNB balance queries (for gas fees)
    - Timeout handling
    """

    def __init__(self, web3: AsyncWeb3, usdt_contract: AsyncContract):
        """
        Initialize balance checker.

        Args:
            web3: AsyncWeb3 instance
            usdt_contract: USDT contract instance
        """
        self.web3 = web3
        self.usdt_contract = usdt_contract

    async def get_usdt_balance(
        self,
        address: str,
    ) -> Decimal | None:
        """
        Get USDT balance for address.

        Args:
            address: Wallet address

        Returns:
            USDT balance or None
        """
        try:
            check_address_checksum = self.web3.to_checksum_address(
                address
            )

            # Get balance with timeout
            try:
                balance_wei = await asyncio.wait_for(
                    self.usdt_contract.functions.balanceOf(
                        check_address_checksum
                    ).call(),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except TimeoutError:
                logger.error(f"Timeout getting USDT balance for {mask_address(address)}")
                return None

            balance_usdt = Decimal(balance_wei) / Decimal(10**USDT_DECIMALS)

            return balance_usdt

        except Exception as e:
            logger.error(f"Error getting USDT balance: {e}")
            return None

    async def get_bnb_balance(
        self,
        address: str,
    ) -> Decimal | None:
        """
        Get BNB balance for address (for gas fees).

        Args:
            address: Wallet address

        Returns:
            BNB balance or None
        """
        try:
            check_address_checksum = self.web3.to_checksum_address(
                address
            )

            # Get BNB balance with timeout
            try:
                balance_wei = await asyncio.wait_for(
                    self.web3.eth.get_balance(
                        check_address_checksum
                    ),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except TimeoutError:
                logger.error(f"Timeout getting BNB balance for {mask_address(address)}")
                return None

            balance_bnb = Decimal(
                str(self.web3.from_wei(balance_wei, "ether"))
            )

            return balance_bnb

        except Exception as e:
            logger.error(f"Error getting BNB balance: {e}")
            return None
