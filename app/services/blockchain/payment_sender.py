"""
Payment Sender.

Handles USDT payment sending with gas estimation and error handling.
"""

import asyncio
from decimal import Decimal
from typing import Any

from eth_account import Account
from loguru import logger
from web3 import AsyncWeb3
from web3.exceptions import ContractLogicError

from .constants import (
    DEFAULT_GAS_LIMIT,
    MAX_GAS_PRICE_GWEI,
    MAX_RETRIES,
    RETRY_DELAY_BASE,
    USDT_ABI,
    USDT_DECIMALS,
)
from app.config.constants import BLOCKCHAIN_TIMEOUT
from app.utils.security import mask_address


class PaymentSender:
    """
    Handles USDT payment sending on BSC.

    Features:
    - Gas estimation
    - Nonce management
    - Retry with exponential backoff
    - Transaction tracking
    """

    def __init__(
        self,
        web3: AsyncWeb3,
        usdt_contract_address: str,
        payout_wallet_private_key: str | None = None,
    ) -> None:
        """
        Initialize payment sender.

        Args:
            web3: AsyncWeb3 instance
            usdt_contract_address: USDT contract address
            payout_wallet_private_key: Private key for signing transactions
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

        if self._private_key:
            # Derive address from private key
            account = Account.from_key(self._private_key)
            self._payout_address = account.address
            logger.info(
                f"PaymentSender initialized with wallet: "
                f"{self._payout_address}"
            )
        else:
            logger.warning(
                "PaymentSender initialized without private key - "
                "sending will not work"
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
            prev_status = await self.check_transaction_status(previous_tx_hash)

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
        from decimal import ROUND_DOWN
        amount_wei = int((Decimal(str(amount_usdt)) * Decimal(10 ** USDT_DECIMALS)).to_integral_value(ROUND_DOWN))

        logger.info(
            f"Sending {amount_usdt} USDT to {to_address_checksum}\n"
            f"  From: {self._payout_address}\n"
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
                    prev_status = await self.check_transaction_status(
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
                # Get nonce from pending block for better concurrency with timeout
                try:
                    nonce = await asyncio.wait_for(
                        self.web3.eth.get_transaction_count(
                            self._payout_address, 'pending'
                        ),
                        timeout=BLOCKCHAIN_TIMEOUT,
                    )
                except asyncio.TimeoutError:
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
                            {"from": self._payout_address}
                        ),
                        timeout=BLOCKCHAIN_TIMEOUT,
                    )
                    # Add 20% buffer
                    gas_limit = int(gas_estimate * 1.2)
                except asyncio.TimeoutError:
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
                except asyncio.TimeoutError:
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
                                "from": self._payout_address,
                                "gas": gas_limit,
                                "gasPrice": gas_price_wei,
                                "nonce": nonce,
                            }
                        ),
                        timeout=BLOCKCHAIN_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    logger.error("Timeout building transaction")
                    return {
                        "success": False,
                        "tx_hash": None,
                        "error": "Timeout building transaction",
                    }

                # Sign transaction
                account = Account.from_key(self._private_key)
                signed_tx = account.sign_transaction(transaction)

                # Send transaction with timeout
                try:
                    tx_hash = await asyncio.wait_for(
                        self.web3.eth.send_raw_transaction(
                            signed_tx.rawTransaction
                        ),
                        timeout=BLOCKCHAIN_TIMEOUT,
                    )
                except asyncio.TimeoutError:
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
        try:
            to_address_checksum = self.web3.to_checksum_address(to_address)
            # Convert Decimal to wei using proper precision handling
            from decimal import ROUND_DOWN
            amount_wei = int((Decimal(str(amount_usdt)) * Decimal(10 ** USDT_DECIMALS)).to_integral_value(ROUND_DOWN))

            # Estimate gas with timeout
            transfer_function = self.usdt_contract.functions.transfer(
                to_address_checksum,
                amount_wei,
            )

            try:
                gas_estimate = await asyncio.wait_for(
                    transfer_function.estimate_gas(
                        {"from": self._payout_address}
                    ),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.error("Timeout estimating gas cost")
                return None

            # Get gas price with timeout
            try:
                gas_price_wei = await asyncio.wait_for(
                    self.web3.eth.gas_price,
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.error("Timeout getting gas price for cost estimation")
                return None

            # Calculate total cost in BNB
            total_cost_wei = gas_estimate * gas_price_wei
            total_cost_bnb = self.web3.from_wei(total_cost_wei, "ether")

            return {
                "gas_limit": gas_estimate,
                "gas_price_gwei": float(
                    self.web3.from_wei(gas_price_wei, "gwei")
                ),
                "total_cost_bnb": float(total_cost_bnb),
            }

        except Exception as e:
            logger.error(f"Error estimating gas: {e}")
            return None

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
        try:
            check_address = address or self._payout_address
            if not check_address:
                return None

            check_address_checksum = self.web3.to_checksum_address(
                check_address
            )

            # Get balance with timeout
            try:
                balance_wei = await asyncio.wait_for(
                    self.usdt_contract.functions.balanceOf(
                        check_address_checksum
                    ).call(),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout getting USDT balance for {mask_address(check_address)}")
                return None

            balance_usdt = Decimal(balance_wei) / Decimal(10**USDT_DECIMALS)

            return balance_usdt

        except Exception as e:
            logger.error(f"Error getting USDT balance: {e}")
            return None

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
        try:
            check_address = address or self._payout_address
            if not check_address:
                return None

            check_address_checksum = self.web3.to_checksum_address(
                check_address
            )

            # Get BNB balance with timeout
            try:
                balance_wei = await asyncio.wait_for(
                    self.web3.eth.get_balance(
                        check_address_checksum
                    ),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout getting BNB balance for {mask_address(check_address)}")
                return None

            balance_bnb = Decimal(
                str(self.web3.from_wei(balance_wei, "ether"))
            )

            return balance_bnb

        except Exception as e:
            logger.error(f"Error getting BNB balance: {e}")
            return None

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
        try:
            logger.info(f"Checking status of transaction: {tx_hash}")

            # Try to get transaction receipt with timeout
            try:
                receipt = await asyncio.wait_for(
                    self.web3.eth.get_transaction_receipt(tx_hash),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout getting transaction receipt for {tx_hash}")
                return None

            if receipt:
                status = "confirmed" if receipt["status"] == 1 else "failed"
                logger.info(
                    f"Transaction {tx_hash} status: {status}, "
                    f"block: {receipt['blockNumber']}"
                )

                return {
                    "status": status,
                    "success": receipt["status"] == 1,
                    "tx_hash": tx_hash,
                    "block_number": receipt["blockNumber"],
                    "gas_used": receipt["gasUsed"],
                }

            # Transaction exists but not mined yet - check with timeout
            try:
                tx = await asyncio.wait_for(
                    self.web3.eth.get_transaction(tx_hash),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout getting transaction for {tx_hash}")
                return None

            if tx:
                logger.info(
                    f"Transaction {tx_hash} pending (not yet mined)"
                )
                return {
                    "status": "pending",
                    "success": False,
                    "tx_hash": tx_hash,
                }

            return None

        except Exception as e:
            logger.warning(f"Could not check transaction {tx_hash}: {e}")
            return None
