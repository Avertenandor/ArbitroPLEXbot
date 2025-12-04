"""
Payment Sender.

Handles USDT payment sending with gas estimation and error handling.
"""

import asyncio
import ctypes
from decimal import Decimal
from typing import Any

from eth_account import Account
from loguru import logger
from web3 import AsyncWeb3
from web3.exceptions import ContractLogicError

from app.config.constants import BLOCKCHAIN_TIMEOUT
from app.utils.security import mask_address

from .constants import (
    DEFAULT_GAS_LIMIT,
    MAX_GAS_PRICE_GWEI,
    MAX_RETRIES,
    RETRY_DELAY_BASE,
    USDT_ABI,
    USDT_DECIMALS,
)


def secure_zero_memory(secret: str) -> None:
    """
    Securely overwrite memory containing secret data.

    NOTE: This provides best-effort memory clearing in Python.
    Python's memory management makes true secure erasure impossible,
    but this reduces the window of exposure.
    """
    if not secret:
        return

    try:
        # Convert to bytes if string
        secret_bytes = secret.encode() if isinstance(secret, str) else secret
        # Overwrite with zeros
        ctypes.memset(id(secret_bytes) + 32, 0, len(secret_bytes))
    except Exception:
        # Fail silently - this is best-effort security
        pass


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

    async def _get_safe_nonce(self, address: str) -> int:
        """
        Get nonce with stuck transaction detection.

        Args:
            address: Wallet address

        Returns:
            Safe nonce to use
        """
        # Get pending nonce (includes pending transactions)
        pending_nonce = await self.web3.eth.get_transaction_count(address, 'pending')
        # Get confirmed nonce (only confirmed transactions)
        confirmed_nonce = await self.web3.eth.get_transaction_count(address, 'latest')

        # If there are too many stuck transactions (pending > confirmed + threshold)
        stuck_threshold = 5
        if pending_nonce > confirmed_nonce + stuck_threshold:
            logger.warning(
                f"Possible stuck transactions detected: "
                f"pending={pending_nonce}, confirmed={confirmed_nonce}, "
                f"stuck={pending_nonce - confirmed_nonce}"
            )

        return pending_nonce

    async def _get_nonce_with_distributed_lock(
        self,
        address: str,
        session_factory: Any = None
    ) -> int:
        """
        Get nonce with distributed lock for multi-instance protection.

        Uses Redis-based distributed lock to prevent nonce conflicts
        when multiple bot instances are running.

        Args:
            address: Wallet address
            session_factory: Session factory for distributed lock (optional)

        Returns:
            Safe nonce to use
        """
        from app.utils.distributed_lock import get_distributed_lock

        # Create lock key specific to this address
        lock_key = f"nonce_lock:{address}"

        # Try to get distributed lock with Redis/PostgreSQL
        if session_factory:
            async with session_factory() as session:
                distributed_lock = get_distributed_lock(session=session)

                # Acquire distributed lock with timeout
                async with distributed_lock.lock(
                    key=lock_key,
                    timeout=30,  # Lock expires after 30 seconds
                    blocking=True,
                    blocking_timeout=10.0  # Wait max 10 seconds for lock
                ):
                    # Get nonce inside the distributed lock
                    return await self._get_safe_nonce(address)
        else:
            # Fallback to no distributed lock if no session factory
            logger.debug("No session factory available, using local lock only")
            return await self._get_safe_nonce(address)

    async def _prepare_payment(
        self, to_address: str, amount_usdt: Decimal
    ) -> dict[str, Any]:
        """
        Prepare payment by validating address and converting amount.

        Args:
            to_address: Recipient address
            amount_usdt: Amount in USDT

        Returns:
            Dict with to_address_checksum, amount_wei, or error
        """
        # Validate and checksum address
        try:
            to_address_checksum = self.web3.to_checksum_address(to_address)
        except Exception as e:
            return {"error": f"Invalid address: {e}"}

        # Convert amount to wei (18 decimals for BSC USDT)
        from decimal import ROUND_DOWN

        amount_wei = int(
            (Decimal(str(amount_usdt)) * Decimal(10**USDT_DECIMALS)).to_integral_value(
                ROUND_DOWN
            )
        )

        return {
            "to_address_checksum": to_address_checksum,
            "amount_wei": amount_wei,
        }

    async def _check_previous_transaction(
        self, tx_hash: str
    ) -> dict[str, Any] | None:
        """
        Check if a previous transaction succeeded or is still pending.

        Args:
            tx_hash: Transaction hash to check

        Returns:
            Result dict if transaction succeeded/pending, None otherwise
        """
        logger.info(f"Checking status of previous transaction: {tx_hash}")
        prev_status = await self.check_transaction_status(tx_hash)

        if not prev_status:
            return None

        # Transaction already succeeded
        if prev_status["success"]:
            logger.success(
                f"Previous transaction {tx_hash} already confirmed - no need to retry"
            )
            return prev_status

        # Transaction still pending - wait a bit more
        if prev_status["status"] == "pending":
            logger.info(f"Previous transaction {tx_hash} still pending, waiting...")
            try:
                receipt = await asyncio.wait_for(
                    self.web3.eth.wait_for_transaction_receipt(tx_hash),
                    timeout=60,
                )
                if receipt["status"] == 1:
                    return {
                        "success": True,
                        "tx_hash": tx_hash,
                        "block_number": receipt["blockNumber"],
                        "gas_used": receipt["gasUsed"],
                    }
            except TimeoutError:
                logger.warning(
                    f"Previous transaction {tx_hash} "
                    f"still not confirmed after additional wait"
                )

        return None

    async def _handle_payment_result(
        self, result: dict[str, Any], amount_usdt: Decimal
    ) -> dict[str, Any] | None:
        """
        Handle payment result and determine if retry is needed.

        Args:
            result: Transaction result
            amount_usdt: Amount in USDT for logging

        Returns:
            Result dict if payment succeeded or pending, None if retry needed
        """
        if result["success"]:
            logger.success(
                f"Payment sent successfully!\n"
                f"  TX: {result['tx_hash']}\n"
                f"  Amount: {amount_usdt} USDT"
            )
            return result

        if result.get("status") == "pending":
            logger.warning(
                f"Transaction {result.get('tx_hash')} pending - "
                f"returning for later check"
            )
            return result

        return None

    async def _perform_payment_attempt(
        self,
        to_address_checksum: str,
        amount_wei: int,
        amount_usdt: Decimal,
        attempt: int,
        last_tx_hash: str | None,
    ) -> dict[str, Any]:
        """
        Perform a single payment attempt with previous transaction check.

        Args:
            to_address_checksum: Checksummed recipient address
            amount_wei: Amount in wei
            amount_usdt: Amount in USDT for logging
            attempt: Current attempt number (0-indexed)
            last_tx_hash: Previous transaction hash to check

        Returns:
            Dict with result and updated last_tx_hash
        """
        # Before retrying, check if previous transaction succeeded
        if attempt > 0 and last_tx_hash:
            logger.info(
                f"Checking previous transaction {last_tx_hash} "
                f"before retry attempt {attempt + 1}"
            )
            prev_status = await self.check_transaction_status(last_tx_hash)
            if prev_status and prev_status["success"]:
                logger.success(
                    f"Previous transaction {last_tx_hash} "
                    f"confirmed - no retry needed"
                )
                return {"result": prev_status, "last_tx_hash": last_tx_hash}

        # Send transaction
        result = await self._send_transaction(
            to_address_checksum,
            amount_wei,
        )

        # Update last_tx_hash
        new_last_tx_hash = result.get("tx_hash") or last_tx_hash

        return {"result": result, "last_tx_hash": new_last_tx_hash}

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
        # Early return if no private key
        if not self._private_key:
            return {
                "success": False,
                "tx_hash": None,
                "error": "Private key not configured",
            }

        # Check if previous transaction already succeeded
        if previous_tx_hash:
            prev_result = await self._check_previous_transaction(previous_tx_hash)
            if prev_result:
                return prev_result

        # Prepare payment data
        prepared = await self._prepare_payment(to_address, amount_usdt)
        if "error" in prepared:
            return {
                "success": False,
                "tx_hash": None,
                "error": prepared["error"],
            }

        to_address_checksum = prepared["to_address_checksum"]
        amount_wei = prepared["amount_wei"]

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
                # Perform payment attempt
                attempt_result = await self._perform_payment_attempt(
                    to_address_checksum,
                    amount_wei,
                    amount_usdt,
                    attempt,
                    last_tx_hash,
                )

                result = attempt_result["result"]
                last_tx_hash = attempt_result["last_tx_hash"]

                # Handle result (returns None if retry needed)
                final_result = await self._handle_payment_result(result, amount_usdt)
                if final_result:
                    return final_result

                # Retry with exponential backoff
                if attempt < max_retries - 1:
                    delay = RETRY_DELAY_BASE ** (attempt + 1)
                    logger.warning(
                        f"Payment attempt {attempt + 1} failed, retrying in {delay}s..."
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

    async def _get_nonce(self) -> dict[str, Any]:
        """
        Get nonce for transaction with distributed lock support.

        Returns:
            Dict with nonce or error
        """
        try:
            if self._session_factory:
                nonce = await asyncio.wait_for(
                    self._get_nonce_with_distributed_lock(
                        self._payout_address, self._session_factory
                    ),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            else:
                nonce = await asyncio.wait_for(
                    self._get_safe_nonce(self._payout_address),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            logger.debug(
                f"Acquired nonce {nonce} for {mask_address(self._payout_address)}"
            )
            return {"nonce": nonce}
        except TimeoutError:
            logger.error("Timeout getting transaction count (nonce)")
            return {"error": "Timeout getting nonce"}

    async def _get_gas_params(
        self, transfer_function: Any
    ) -> dict[str, Any]:
        """
        Get gas limit and gas price for transaction.

        Args:
            transfer_function: Contract transfer function

        Returns:
            Dict with gas_limit, gas_price_wei, or error
        """
        # Estimate gas with timeout
        try:
            gas_estimate = await asyncio.wait_for(
                transfer_function.estimate_gas({"from": self._payout_address}),
                timeout=BLOCKCHAIN_TIMEOUT,
            )
            gas_limit = int(gas_estimate * 1.2)  # Add 20% buffer
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
            return {"error": "Timeout getting gas price"}

        # Cap gas price
        max_gas_price = self.web3.to_wei(MAX_GAS_PRICE_GWEI, "gwei")
        if gas_price_wei > max_gas_price:
            logger.warning(
                f"Gas price {gas_price_wei} exceeds max {max_gas_price}, using max"
            )
            gas_price_wei = max_gas_price

        return {"gas_limit": gas_limit, "gas_price_wei": gas_price_wei}

    async def _build_transaction(
        self,
        transfer_function: Any,
        nonce: int,
        gas_limit: int,
        gas_price_wei: int,
    ) -> dict[str, Any]:
        """
        Build transaction dictionary.

        Args:
            transfer_function: Contract transfer function
            nonce: Transaction nonce
            gas_limit: Gas limit
            gas_price_wei: Gas price in wei

        Returns:
            Dict with transaction or error
        """
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
            return {"transaction": transaction}
        except TimeoutError:
            logger.error("Timeout building transaction")
            return {"error": "Timeout building transaction"}

    async def _execute_transaction(
        self, transaction: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Sign and send transaction to blockchain.

        Args:
            transaction: Transaction dictionary to sign and send

        Returns:
            Dict with tx_hash or error
        """
        # SECURITY: Sign transaction with minimal Account lifetime
        account = None
        try:
            account = Account.from_key(self._private_key)
            signed_tx = account.sign_transaction(transaction)
        finally:
            if account:
                del account

        # Send transaction with timeout
        try:
            tx_hash = await asyncio.wait_for(
                self.web3.eth.send_raw_transaction(signed_tx.rawTransaction),
                timeout=BLOCKCHAIN_TIMEOUT,
            )
            return {"tx_hash": tx_hash.hex()}
        except TimeoutError:
            logger.error("Timeout sending raw transaction")
            return {"error": "Timeout sending transaction"}

    async def _wait_for_receipt(self, tx_hash_hex: str) -> dict[str, Any]:
        """
        Wait for transaction receipt and return result.

        Args:
            tx_hash_hex: Transaction hash in hex format

        Returns:
            Dict with success, tx_hash, and additional data
        """
        try:
            receipt = await asyncio.wait_for(
                self.web3.eth.wait_for_transaction_receipt(tx_hash_hex),
                timeout=120,  # 2 minutes
            )

            if receipt["status"] == 1:
                return {
                    "success": True,
                    "tx_hash": tx_hash_hex,
                    "block_number": receipt["blockNumber"],
                    "gas_used": receipt["gasUsed"],
                }

            return {
                "success": False,
                "tx_hash": tx_hash_hex,
                "error": "Transaction reverted",
                "status": "failed",
            }

        except TimeoutError:
            # IMPORTANT: Timeout does NOT mean transaction failed!
            logger.warning(
                f"Transaction {tx_hash_hex} confirmation timeout - "
                f"transaction may still be pending"
            )
            return {
                "success": False,
                "tx_hash": tx_hash_hex,
                "error": "Transaction confirmation timeout - check status later",
                "status": "pending",
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
                # Get nonce
                nonce_result = await self._get_nonce()
                if "error" in nonce_result:
                    return {
                        "success": False,
                        "tx_hash": None,
                        "error": nonce_result["error"],
                    }
                nonce = nonce_result["nonce"]

                # Build transfer function
                transfer_function = self.usdt_contract.functions.transfer(
                    to_address,
                    amount_wei,
                )

                # Get gas parameters
                gas_result = await self._get_gas_params(transfer_function)
                if "error" in gas_result:
                    return {
                        "success": False,
                        "tx_hash": None,
                        "error": gas_result["error"],
                    }
                gas_limit = gas_result["gas_limit"]
                gas_price_wei = gas_result["gas_price_wei"]

                # Build transaction
                tx_result = await self._build_transaction(
                    transfer_function, nonce, gas_limit, gas_price_wei
                )
                if "error" in tx_result:
                    return {
                        "success": False,
                        "tx_hash": None,
                        "error": tx_result["error"],
                    }
                transaction = tx_result["transaction"]

                # Execute transaction (sign and send)
                exec_result = await self._execute_transaction(transaction)
                if "error" in exec_result:
                    return {
                        "success": False,
                        "tx_hash": None,
                        "error": exec_result["error"],
                    }
                tx_hash_hex = exec_result["tx_hash"]

                logger.info(
                    f"Transaction sent! Hash: {tx_hash_hex}\n"
                    f"  Gas: {gas_limit}\n"
                    f"  Gas Price: {self.web3.from_wei(gas_price_wei, 'gwei')} Gwei"
                )

                # Wait for receipt
                return await self._wait_for_receipt(tx_hash_hex)

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

            amount_wei = int(
                (Decimal(str(amount_usdt)) * Decimal(10**USDT_DECIMALS)).to_integral_value(
                    ROUND_DOWN
                )
            )

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
            except TimeoutError:
                logger.error("Timeout estimating gas cost")
                return None

            # Get gas price with timeout
            try:
                gas_price_wei = await asyncio.wait_for(
                    self.web3.eth.gas_price,
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except TimeoutError:
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
            except TimeoutError:
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
            except TimeoutError:
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
            except TimeoutError:
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
            except TimeoutError:
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
