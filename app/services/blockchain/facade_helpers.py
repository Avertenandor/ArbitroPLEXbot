"""
Blockchain service - Helper methods mixin.

This module provides BlockchainServiceMixin with delegating methods for:
- Wallet operations (validation)
- Balance operations (USDT, PLEX, BNB)
- Gas operations (estimation)
- Transaction operations (send, status, details)
- Payment verification (PLEX, USDT deposits)
- Block operations (current block number)
"""

import asyncio
from decimal import Decimal
from typing import Any

from loguru import logger
from web3 import Web3
from web3.exceptions import Web3Exception


class BlockchainServiceMixin:
    """
    Mixin class with delegating methods for blockchain operations.

    This class provides convenience methods that delegate to specialized
    managers (BalanceManager, TransactionManager, PaymentVerifier, etc.).
    """

    # ========== Wallet Methods ==========

    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate wallet address format.

        Args:
            address: Wallet address to validate

        Returns:
            True if address is valid
        """
        return await self.wallet_manager.validate_wallet_address(address)

    # ========== Balance Methods ==========

    async def get_usdt_balance(self, address: str) -> Decimal | None:
        """
        Get USDT balance for address.

        Args:
            address: Wallet address

        Returns:
            USDT balance or None on error
        """
        try:
            def _get_bal(w3: Web3):
                return self.balance_manager.get_usdt_balance(w3, address)

            return await self.async_executor.run_with_failover(_get_bal)
        except (
            Web3Exception, ValueError, TimeoutError,
            ConnectionError, OSError
        ) as error:
            logger.error(f"Get USDT balance failed for {address}: {error}")
            return None

    async def get_plex_balance(self, address: str) -> Decimal | None:
        """
        Get PLEX token balance for address.

        Args:
            address: Wallet address

        Returns:
            PLEX balance or None on error
        """
        try:
            def _get_bal(w3: Web3):
                return self.balance_manager.get_plex_balance(w3, address)

            return await self.async_executor.run_with_failover(_get_bal)
        except (
            Web3Exception, ValueError, TimeoutError,
            ConnectionError, OSError
        ) as error:
            logger.error(f"Get PLEX balance failed for {address}: {error}")
            return None

    async def get_native_balance(self, address: str) -> Decimal | None:
        """
        Get Native Token (BNB) balance.

        Args:
            address: Wallet address

        Returns:
            BNB balance or None on error
        """
        try:
            def _get_bal(w3: Web3):
                return self.balance_manager.get_native_balance(w3, address)

            return await self.async_executor.run_with_failover(_get_bal)
        except (Web3Exception, ValueError, TimeoutError, ConnectionError, OSError) as error:
            logger.error(f"Get BNB balance failed for {address}: {error}")
            return None

    # ========== Gas Methods ==========

    async def estimate_gas_fee(
        self,
        to_address: str,
        amount: Decimal
    ) -> Decimal | None:
        """
        Estimate gas fee for USDT transfer.

        Args:
            to_address: Recipient wallet address
            amount: Amount in USDT (Decimal)

        Returns:
            Estimated gas fee in BNB or None
        """
        try:
            def _est_gas(w3: Web3):
                return self.gas_manager.estimate_gas_fee(
                    w3, to_address, amount, self.wallet_address
                )

            return await self.async_executor.run_with_failover(_est_gas)
        except (Web3Exception, ValueError, TimeoutError, ConnectionError, OSError) as error:
            logger.error(f"Estimate gas fee failed for {to_address} amount {amount}: {error}")
            return None

    # ========== Transaction Methods ==========

    async def send_payment(
        self,
        to_address: str,
        amount: Decimal
    ) -> dict[str, Any]:
        """
        Send USDT payment.

        Args:
            to_address: Recipient wallet address
            amount: Amount in USDT (Decimal for precision)

        Returns:
            Dict with success, tx_hash, error
        """
        if not await self.validate_wallet_address(to_address):
            return {
                "success": False,
                "error": f"Invalid address: {to_address}"
            }

        def _send(w3: Web3):
            return asyncio.run(
                self.transaction_manager.send_usdt_payment(
                    w3, to_address, amount, self.async_executor._executor
                )
            )

        try:
            return await self.async_executor.run_with_failover(_send)
        except (Web3Exception, ValueError, TimeoutError, ConnectionError, OSError) as error:
            logger.error(f"Failed to send payment to {to_address} amount {amount}: {error}")
            return {"success": False, "error": str(error)}

    async def send_native_token(
        self,
        to_address: str,
        amount: Decimal
    ) -> dict[str, Any]:
        """
        Send native token (BNB) to address.

        Args:
            to_address: Recipient wallet address
            amount: Amount in BNB (Decimal for precision)

        Returns:
            Dict with success, tx_hash, error
        """
        if not await self.validate_wallet_address(to_address):
            return {
                "success": False,
                "error": f"Invalid address: {to_address}"
            }

        def _send(w3: Web3):
            return asyncio.run(
                self.transaction_manager.send_native_token(
                    w3, to_address, amount, self.async_executor._executor
                )
            )

        try:
            return await self.async_executor.run_with_failover(_send)
        except (Web3Exception, ValueError, TimeoutError, ConnectionError, OSError) as error:
            logger.error(f"Failed to send BNB to {to_address} amount {amount}: {error}")
            return {"success": False, "error": str(error)}

    async def check_transaction_status(
        self,
        tx_hash: str
    ) -> dict[str, Any]:
        """
        Check transaction status.

        Args:
            tx_hash: Transaction hash

        Returns:
            Dict with status, confirmations, block_number
        """
        try:
            def _check(w3: Web3):
                return self.transaction_manager.check_transaction_status_sync(
                    w3, tx_hash
                )

            return await self.async_executor.run_with_failover(_check)
        except (TimeoutError, Web3Exception) as error:
            logger.warning(f"Failed to check transaction status: {error}")
            return {"status": "unknown", "confirmations": 0}

    async def get_transaction_details(
        self,
        tx_hash: str
    ) -> dict[str, Any] | None:
        """
        Get transaction details.

        Args:
            tx_hash: Transaction hash

        Returns:
            Dict with transaction details or None on error
        """
        try:
            def _fetch(w3: Web3):
                return self.transaction_manager.get_transaction_details_sync(
                    w3, tx_hash
                )

            return await self.async_executor.run_with_failover(_fetch)
        except (TimeoutError, Web3Exception) as error:
            logger.warning(f"Failed to get transaction details: {error}")
            return None

    # ========== Payment Verification Methods ==========

    async def verify_plex_payment(
        self,
        sender_address: str,
        amount_plex: float | Decimal | None = None,
        lookback_blocks: int = 200,  # ~10 minutes on BSC (3 sec/block)
    ) -> dict[str, Any]:
        """
        Verify if user paid PLEX tokens to system wallet.

        Args:
            sender_address: User's wallet address
            amount_plex: Required PLEX amount (uses default if None)
            lookback_blocks: Number of blocks to scan back

        Returns:
            Dict with success, tx_hash, amount, block, or error
        """
        target_amount = (
            amount_plex
            if amount_plex is not None
            else self.settings.auth_price_plex
        )

        def _verify(w3: Web3):
            return self.payment_verifier.verify_plex_payment_sync(
                w3, sender_address, target_amount, lookback_blocks
            )

        try:
            return await self.async_executor.run_with_failover(_verify)
        except (
            Web3Exception, ValueError, TimeoutError,
            ConnectionError, OSError
        ) as error:
            logger.error(
                f"[PLEX Verify] Failed for sender {sender_address} "
                f"amount {target_amount}: {error}"
            )
            return {"success": False, "error": str(error)}

    async def get_user_usdt_deposits(
        self,
        user_wallet: str,
        max_blocks: int = 100000,
    ) -> dict:
        """
        Scan all USDT Transfer events from user wallet to system wallet.

        Used to detect user's total deposit amount from blockchain history.

        Args:
            user_wallet: User's wallet address
            max_blocks: Maximum number of blocks to scan back

        Returns:
            Dict with total_amount, tx_count, transactions, success, error
        """
        def _scan(w3: Web3):
            return self.payment_verifier.scan_usdt_deposits_sync(
                w3, user_wallet, max_blocks
            )

        try:
            return await self.async_executor.run_with_failover(_scan)
        except (Web3Exception, ValueError, TimeoutError, ConnectionError, OSError) as error:
            logger.error(f"Deposit scan failed for wallet {user_wallet}: {error}")
            return {
                'success': False,
                'error': str(error),
                'total_amount': Decimal("0"),
                'tx_count': 0,
                'transactions': [],
            }

    async def verify_plex_transfer(
        self,
        from_address: str,
        amount: Decimal,
        lookback_blocks: int = 200,
    ) -> dict[str, Any]:
        """
        Verify PLEX token transfer from address to system wallet.

        Args:
            from_address: Sender's wallet address
            amount: Required PLEX amount (Decimal)
            lookback_blocks: Number of blocks to scan back

        Returns:
            Dict with success, tx_hash, amount, block, timestamp, or error
        """
        def _verify(w3: Web3):
            return self.payment_verifier.verify_plex_transfer(
                w3, from_address, amount, lookback_blocks
            )

        try:
            return await self.async_executor.run_with_failover(_verify)
        except (
            Web3Exception, ValueError, TimeoutError,
            ConnectionError, OSError
        ) as error:
            logger.error(
                f"[PLEX Transfer Verify] Failed for sender "
                f"{from_address} amount {amount}: {error}"
            )
            return {"success": False, "error": str(error)}

    async def scan_plex_payments(
        self,
        from_address: str,
        since_block: int | None = None,
        max_blocks: int = 100000,
    ) -> list[dict[str, Any]]:
        """
        Scan all PLEX Transfer events from user wallet to system wallet.

        Args:
            from_address: User's wallet address
            since_block: Starting block number (if None, scan from max ago)
            max_blocks: Maximum number of blocks to scan back

        Returns:
            List of payment dictionaries with tx_hash, amount, block
        """
        def _scan(w3: Web3):
            return self.payment_verifier.scan_plex_payments(
                w3, from_address, since_block, max_blocks
            )

        try:
            return await self.async_executor.run_with_failover(_scan)
        except (Web3Exception, ValueError, TimeoutError, ConnectionError, OSError) as error:
            logger.error(f"[PLEX Scan] Failed for sender {from_address}: {error}")
            return []

    # ========== Block Operations ==========

    async def get_block_number(self) -> int:
        """
        Get current block number.

        Returns:
            Current block number
        """
        return await self.block_operations.get_block_number()
