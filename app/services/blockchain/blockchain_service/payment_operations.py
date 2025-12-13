"""
Payment Operations Module.

Contains all payment-related functionality for the BlockchainService.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..payment_sender import PaymentSender


class PaymentOperations:
    """
    Handles payment-related operations.

    Features:
    - USDT payment sending
    - Gas cost estimation
    """

    def __init__(self, payment_sender: "PaymentSender") -> None:
        """
        Initialize payment operations.

        Args:
            payment_sender: PaymentSender instance
        """
        self.payment_sender = payment_sender

    async def send_payment(
        self,
        to_address: str,
        amount_usdt: Decimal,
        max_retries: int = 5,
        previous_tx_hash: str | None = None,
    ) -> dict[str, Any]:
        """
        Send USDT payment.

        Args:
            to_address: Recipient wallet address
            amount_usdt: Amount in USDT (Decimal)
            max_retries: Maximum retry attempts
            previous_tx_hash: Previous transaction hash to check before retry

        Returns:
            Dict with success, tx_hash, error
        """
        return await self.payment_sender.send_payment(
            to_address=to_address,
            amount_usdt=amount_usdt,
            max_retries=max_retries,
            previous_tx_hash=previous_tx_hash,
        )

    async def estimate_gas_cost(
        self,
        to_address: str,
        amount_usdt: Decimal,
    ) -> dict[str, Any] | None:
        """
        Estimate gas cost for payment.

        Args:
            to_address: Recipient address
            amount_usdt: Amount in USDT (Decimal)

        Returns:
            Dict with gas_limit, gas_price_gwei, total_cost_bnb
        """
        return await self.payment_sender.estimate_gas_cost(
            to_address=to_address,
            amount_usdt=amount_usdt,
        )
