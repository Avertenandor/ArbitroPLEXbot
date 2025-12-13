"""
Balance Operations Module.

Contains all balance query functionality for the BlockchainService.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..payment_sender import PaymentSender


class BalanceOperations:
    """
    Handles balance query operations.

    Features:
    - USDT balance queries
    - BNB balance queries
    """

    def __init__(self, payment_sender: PaymentSender) -> None:
        """
        Initialize balance operations.

        Args:
            payment_sender: PaymentSender instance
        """
        self.payment_sender = payment_sender

    async def get_usdt_balance(
        self,
        address: str | None = None,
    ) -> Decimal | None:
        """
        Get USDT balance for address.

        Args:
            address: Wallet address (payout wallet if None)

        Returns:
            USDT balance or None
        """
        return await self.payment_sender.get_usdt_balance(address)

    async def get_bnb_balance(
        self,
        address: str | None = None,
    ) -> Decimal | None:
        """
        Get BNB balance for address (for gas fees).

        Args:
            address: Wallet address (payout wallet if None)

        Returns:
            BNB balance or None
        """
        return await self.payment_sender.get_bnb_balance(address)
