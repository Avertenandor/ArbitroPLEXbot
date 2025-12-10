"""
Transaction Sender for Payment Sender.

Handles the core transaction sending logic with retry mechanisms and error handling.
"""

import asyncio
from decimal import ROUND_DOWN, Decimal
from typing import Any

from eth_account import Account
from loguru import logger
from web3 import AsyncWeb3
from web3.contract import AsyncContract
from web3.exceptions import ContractLogicError

from app.config.constants import BLOCKCHAIN_TIMEOUT
from app.utils.security import mask_address

from ..constants import (
    DEFAULT_GAS_LIMIT,
    MAX_GAS_PRICE_GWEI,
    MAX_RETRIES,
    RETRY_DELAY_BASE,
    USDT_DECIMALS,
)
from .nonce_manager import NonceManager
from .transaction_status import TransactionStatusChecker


class TransactionSender:
    """
    Handles USDT transaction sending with retry logic.

    Features:
    - Transaction building and signing
    - Gas estimation and capping
    - Retry with exponential backoff
    - Transaction confirmation
    """

    def __init__(
        self,
        web3: AsyncWeb3,
        usdt_contract: AsyncContract,
        payout_address: str,
        private_key: str,
        nonce_manager: NonceManager,
        status_checker: TransactionStatusChecker,
        nonce_lock: asyncio.Lock,
        session_factory: Any = None,
    ):
        """
        Initialize transaction sender.

        Args:
            web3: AsyncWeb3 instance
            usdt_contract: USDT contract instance
            payout_address: Payout wallet address
            private_key: Private key for signing
            nonce_manager: Nonce manager instance
            status_checker: Transaction status checker instance
            nonce_lock: Lock for nonce acquisition
            session_factory: Session factory for distributed lock (optional)
        """
        self.web3 = web3
        self.usdt_contract = usdt_contract
        self.payout_address = payout_address
        self._private_key = private_key
        self.nonce_manager = nonce_manager
        self.status_checker = status_checker
        self._nonce_lock = nonce_lock
        self._session_factory = session_factory

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
        if not self._private_key:
            return {
                "success": False,
                "tx_hash": None,
                "error": "Private key not configured",
            }

        # Check previous transaction if provided
        if previous_tx_hash:
            logger.info(
                f"Checking status of previous transaction: {previous_tx_hash}"
            )
            prev_status = await self.status_checker.check_transaction_status(previous_tx_hash)

            if prev_status:
                if prev_status["success"]:
                    # Previous transaction already succeeded!
                    logger.success(
                        f"Previous transaction {previous_tx_hash} "
                        f"already confirmed - no need to retry"
                    )
                    return prev_status
                elif prev_status["status"] == "pending":
                    # Still pending, wait a bit more
                    logger.info(
                        f"Previous transaction {previous_tx_hash} "
                        f"still pending, waiting..."
                    )
                    # Wait up to 60 more seconds
                    try:
                        receipt = await asyncio.wait_for(
                            self.web3.eth.wait_for_transaction_receipt(
                                previous_tx_hash
                            ),
                            timeout=60,
                        )
                        if receipt["status"] == 1:
                            return {
                                "success": True,
                                "tx_hash": previous_tx_hash,
                                "block_number": receipt["blockNumber"],
                                "gas_used": receipt["gasUsed"],
                            }
                    except TimeoutError:
                        logger.warning(
                            f"Previous transaction {previous_tx_hash} "
                            f"still not confirmed after additional wait"
                        )

        # Validate and checksum address
        try:
            to_address_checksum = self.web3.to_checksum_address(to_address)
        except Exception as e:
            return {
                "success": False,
                "tx_hash": None,
                "error": f"Invalid address: {e}",
            }

        # Convert amount to wei (18 decimals for BSC USDT)
        # Use Decimal arithmetic throughout to avoid float precision errors
        amount_wei = int((Decimal(str(amount_usdt)) * Decimal(10 ** USDT_DECIMALS)).to_integral_value(ROUND_DOWN))

        logger.info(
            f"Sending {amount_usdt} USDT to {to_address_checksum}\n"
            f"  From: {self.payout_address}\n"
            f"  Amount (wei): {amount_wei}"
        )

        # Track last tx_hash for checking on retry
        last_tx_hash = previous_tx_hash

        # Retry logic
        for attempt in range(max_retries):
            try:
                # Before sending new transaction, check if previous one succeeded
                if attempt > 0 and last_tx_hash:
                    logger.info(
                        f"Checking previous transaction {last_tx_hash} "
                        f"before retry attempt {attempt + 1}"
                    )
                    prev_status = await self.status_checker.check_transaction_status(
                        last_tx_hash
                    )
                    if prev_status and prev_status["success"]:
                        logger.success(
                            f"Previous transaction {last_tx_hash} "
                            f"confirmed - no retry needed"
                        )
                        return prev_status

                result = await self._send_transaction(
                    to_address_checksum,
                    amount_wei,
                )

                # Save tx_hash for next retry check
                if result.get("tx_hash"):
                    last_tx_hash = result["tx_hash"]

                if result["success"]:
                    logger.success(
                        f"Payment sent successfully!\n"
                        f"  TX: {result['tx_hash']}\n"
                        f"  Amount: {amount_usdt} USDT"
                    )
                    return result

                # Check if it's a pending timeout
                if result.get("status") == "pending":
                    logger.warning(
                        f"Transaction {last_tx_hash} pending - "
                        f"returning for later check"
                    )
                    return result

                # If failed, retry
                if attempt < max_retries - 1:
                    delay = RETRY_DELAY_BASE ** (attempt + 1)
                    logger.warning(
                        f"Payment attempt {attempt + 1} failed, "
                        f"retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Payment attempt {attempt + 1} error: {e}")

                if attempt < max_retries - 1:
                    delay = RETRY_DELAY_BASE ** (attempt + 1)
                    await asyncio.sleep(delay)

        return {
            "success": False,
            "tx_hash": last_tx_hash,
            "error": f"Failed after {max_retries} attempts",
        }

    async def _send_transaction(
        self,
        to_address: str,
        amount_wei: int,
    ) -> dict[str, Any]:
        """
        Send a single USDT transaction.

        Args:
            to_address: Recipient address (checksummed)
            amount_wei: Amount in wei

        Returns:
            Dict with success, tx_hash, error
        """
        # Lock nonce acquisition and transaction sending to prevent race conditions
        async with self._nonce_lock:
            try:
                # Get safe nonce with stuck transaction detection
                # Use distributed lock if session_factory is available (multi-instance protection)
                try:
                    if self._session_factory:
                        nonce = await asyncio.wait_for(
                            self.nonce_manager.get_nonce_with_distributed_lock(
                                self.payout_address,
                                self._session_factory
                            ),
                            timeout=BLOCKCHAIN_TIMEOUT,
                        )
                    else:
                        nonce = await asyncio.wait_for(
                            self.nonce_manager.get_safe_nonce(self.payout_address),
                            timeout=BLOCKCHAIN_TIMEOUT,
                        )
                    logger.debug(f"Acquired nonce {nonce} for {mask_address(self.payout_address)}")
                except TimeoutError:
                    logger.error("Timeout getting transaction count (nonce)")
                    return {
                        "success": False,
                        "tx_hash": None,
                        "error": "Timeout getting nonce",
                    }

                # Build transaction
                transfer_function = self.usdt_contract.functions.transfer(
                    to_address,
                    amount_wei,
                )

                # Estimate gas with timeout
                try:
                    gas_estimate = await asyncio.wait_for(
                        transfer_function.estimate_gas(
                            {"from": self.payout_address}
                        ),
                        timeout=BLOCKCHAIN_TIMEOUT,
                    )
                    # Add 20% buffer
                    gas_limit = int(gas_estimate * 1.2)
                except TimeoutError:
                    logger.error("Timeout estimating gas, using default")
                    gas_limit = DEFAULT_GAS_LIMIT
                except ContractLogicError as e:
                    logger.error(f"Gas estimation failed: {e}")
                    gas_limit = DEFAULT_GAS_LIMIT

                # Get gas price with timeout
                try:
                    gas_price_wei = await asyncio.wait_for(
                        self.web3.eth.gas_price,
                        timeout=BLOCKCHAIN_TIMEOUT,
                    )
                except TimeoutError:
                    logger.error("Timeout getting gas price")
                    return {
                        "success": False,
                        "tx_hash": None,
                        "error": "Timeout getting gas price",
                    }

                # Cap gas price
                max_gas_price = self.web3.to_wei(MAX_GAS_PRICE_GWEI, "gwei")
                if gas_price_wei > max_gas_price:
                    logger.warning(
                        f"Gas price {gas_price_wei} exceeds max {max_gas_price}, "
                        f"using max"
                    )
                    gas_price_wei = max_gas_price

                # Build transaction dict with timeout
                try:
                    transaction = await asyncio.wait_for(
                        transfer_function.build_transaction(
                            {
                                "from": self.payout_address,
                                "gas": gas_limit,
                                "gasPrice": gas_price_wei,
                                "nonce": nonce,
                            }
                        ),
                        timeout=BLOCKCHAIN_TIMEOUT,
                    )
                except TimeoutError:
                    logger.error("Timeout building transaction")
                    return {
                        "success": False,
                        "tx_hash": None,
                        "error": "Timeout building transaction",
                    }

                # SECURITY: Sign transaction with minimal Account lifetime
                # Create Account only for signing, then immediately clear it
                account = None
                try:
                    account = Account.from_key(self._private_key)
                    signed_tx = account.sign_transaction(transaction)
                finally:
                    # Clear Account object immediately after signing
                    if account:
                        del account

                # Send transaction with timeout
                try:
                    tx_hash = await asyncio.wait_for(
                        self.web3.eth.send_raw_transaction(
                            signed_tx.rawTransaction
                        ),
                        timeout=BLOCKCHAIN_TIMEOUT,
                    )
                except TimeoutError:
                    logger.error("Timeout sending raw transaction")
                    return {
                        "success": False,
                        "tx_hash": None,
                        "error": "Timeout sending transaction",
                    }

                tx_hash_hex = tx_hash.hex()

                logger.info(
                    f"Transaction sent! Hash: {tx_hash_hex}\n"
                    f"  Gas: {gas_limit}\n"
                    f"  Gas Price: "
                    f"{self.web3.from_wei(gas_price_wei, 'gwei')} Gwei"
                )

                # Wait for receipt (with timeout)
                try:
                    receipt = await asyncio.wait_for(
                        self.web3.eth.wait_for_transaction_receipt(tx_hash),
                        timeout=120,  # 2 minutes
                    )

                    if receipt["status"] == 1:
                        return {
                            "success": True,
                            "tx_hash": tx_hash_hex,
                            "block_number": receipt["blockNumber"],
                            "gas_used": receipt["gasUsed"],
                        }
                    else:
                        return {
                            "success": False,
                            "tx_hash": tx_hash_hex,
                            "error": "Transaction reverted",
                            "status": "failed",
                        }

                except TimeoutError:
                    # IMPORTANT: Timeout does NOT mean transaction failed!
                    # Transaction may still be pending or already confirmed
                    logger.warning(
                        f"Transaction {tx_hash_hex} confirmation timeout - "
                        f"transaction may still be pending"
                    )
                    return {
                        "success": False,
                        "tx_hash": tx_hash_hex,
                        "error": "Transaction confirmation timeout - check status later",
                        "status": "pending",  # Mark as pending, not failed!
                    }

            except Exception as e:
                logger.error(f"Error sending transaction: {e}")
                return {
                    "success": False,
                    "tx_hash": None,
                    "error": str(e),
                }
