"""
Payment Sender Module.

Refactored module structure:
- security_utils.py - Security utilities for handling sensitive data
- nonce_manager.py - Nonce management with distributed locking
- transaction_status.py - Transaction status checking
- balance_checker.py - Balance queries for USDT and BNB
- gas_estimator.py - Gas cost estimation
- transaction_sender.py - Core transaction sending logic
- This file (__init__.py) - Main PaymentSender class orchestrating all components

This module handles USDT payment sending with gas estimation and error handling.
"""

import asyncio
from decimal import Decimal
from typing import Any

from eth_account import Account
from loguru import logger
from web3 import AsyncWeb3

from ..constants import MAX_RETRIES, USDT_ABI
from .balance_checker import BalanceChecker
from .gas_estimator import GasEstimator
from .nonce_manager import NonceManager
from .transaction_sender import TransactionSender
from .transaction_status import TransactionStatusChecker


class PaymentSender:
    """
    Handles USDT payment sending on BSC.

    Features:
    - Gas estimation
    - Nonce management
    - Retry with exponential backoff
    - Transaction tracking

    This is the main orchestrator class that delegates to specialized components.
    """

    def __init__(
        self,
        web3: AsyncWeb3,
        usdt_contract_address: str,
        payout_wallet_private_key: str | None = None,
        session_factory: Any = None,
    ) -> None:
        """
        Initialize payment sender.

        Args:
            web3: AsyncWeb3 instance
            usdt_contract_address: USDT contract address
            payout_wallet_private_key: Private key for signing transactions
            session_factory: Session factory for distributed lock (optional)
        """
        self.web3 = web3
        self.usdt_contract_address = web3.to_checksum_address(
            usdt_contract_address
        )

        # Create contract instance
        self.usdt_contract = self.web3.eth.contract(
            address=self.usdt_contract_address,
            abi=USDT_ABI,
        )

        # Wallet setup
        self._private_key = payout_wallet_private_key
        self._payout_address: str | None = None

        # Nonce lock for preventing race conditions in parallel payments
        self._nonce_lock = asyncio.Lock()

        # Session factory for distributed lock (multi-instance protection)
        self._session_factory = session_factory

        if self._private_key:
            # SECURITY: Minimize lifetime of Account object
            # Derive address from private key and immediately discard Account
            try:
                account = Account.from_key(self._private_key)
                self._payout_address = account.address
                logger.info(
                    f"PaymentSender initialized with wallet: "
                    f"{self._payout_address}"
                )
            finally:
                # Clear account object immediately after use
                del account
        else:
            logger.warning(
                "PaymentSender initialized without private key - "
                "sending will not work"
            )

        # Initialize component services
        self._nonce_manager = NonceManager(web3=web3)
        self._status_checker = TransactionStatusChecker(web3=web3)
        self._balance_checker = BalanceChecker(
            web3=web3,
            usdt_contract=self.usdt_contract,
        )
        self._gas_estimator = GasEstimator(
            web3=web3,
            usdt_contract=self.usdt_contract,
            payout_address=self._payout_address,
        )
        self._transaction_sender = TransactionSender(
            web3=web3,
            usdt_contract=self.usdt_contract,
            payout_address=self._payout_address,
            private_key=self._private_key,
            nonce_manager=self._nonce_manager,
            status_checker=self._status_checker,
            nonce_lock=self._nonce_lock,
            session_factory=self._session_factory,
        )

    async def send_payment(
        self,
        to_address: str,
        amount_usdt: Decimal,
        max_retries: int = MAX_RETRIES,
        previous_tx_hash: str | None = None,
    ) -> dict[str, Any]:
        """
        Send USDT payment.

        Args:
            to_address: Recipient address
            amount_usdt: Amount in USDT
            max_retries: Maximum retry attempts
            previous_tx_hash: Previous transaction hash to check before retry

        Returns:
            Dict with success, tx_hash, error
        """
        return await self._transaction_sender.send_payment(
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
        Estimate gas cost for USDT transfer.

        Args:
            to_address: Recipient address
            amount_usdt: Amount in USDT

        Returns:
            Dict with gas_limit, gas_price, total_cost_bnb
        """
        return await self._gas_estimator.estimate_gas_cost(
            to_address=to_address,
            amount_usdt=amount_usdt,
        )

    async def get_usdt_balance(
        self,
        address: str | None = None,
    ) -> Decimal | None:
        """
        Get USDT balance for address.

        Args:
            address: Wallet address (or payout wallet if None)

        Returns:
            USDT balance or None
        """
        check_address = address or self._payout_address
        if not check_address:
            return None

        return await self._balance_checker.get_usdt_balance(check_address)

    async def get_bnb_balance(
        self,
        address: str | None = None,
    ) -> Decimal | None:
        """
        Get BNB balance for address (for gas fees).

        Args:
            address: Wallet address (or payout wallet if None)

        Returns:
            BNB balance or None
        """
        check_address = address or self._payout_address
        if not check_address:
            return None

        return await self._balance_checker.get_bnb_balance(check_address)

    async def check_transaction_status(
        self, tx_hash: str
    ) -> dict[str, Any] | None:
        """
        Check status of existing transaction.

        Args:
            tx_hash: Transaction hash to check

        Returns:
            Dict with status info or None if not found
        """
        return await self._status_checker.check_transaction_status(tx_hash)


# Re-export for backward compatibility
__all__ = [
    "PaymentSender",
]
