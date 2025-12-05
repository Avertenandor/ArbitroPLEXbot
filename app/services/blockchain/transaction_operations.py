"""
Transaction operations for blockchain service.

This module handles:
- Transaction sending (USDT and native BNB)
- Nonce management with distributed locking
- Transaction status checking
- Transaction details retrieval
"""

import asyncio
from decimal import Decimal, ROUND_DOWN
from typing import Any

from eth_account.signers.local import LocalAccount
from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3
from web3.exceptions import ContractLogicError, Web3Exception

from app.utils.security import mask_address, mask_tx_hash

from .core_constants import (
    DEFAULT_NATIVE_GAS_LIMIT,
    GAS_LIMIT_MULTIPLIER,
    NONCE_STUCK_THRESHOLD,
    USDT_ABI,
    USDT_DECIMALS,
)
from .gas_operations import GasManager


class TransactionManager:
    """
    Manages blockchain transaction operations.
    """

    def __init__(
        self,
        usdt_contract_address: str,
        wallet_account: LocalAccount | None,
        wallet_address: str | None,
        gas_manager: GasManager,
        session_factory: Any | None = None,
    ) -> None:
        """
        Initialize transaction manager.

        Args:
            usdt_contract_address: USDT contract address
            wallet_account: Wallet account for signing transactions
            wallet_address: Wallet address
            gas_manager: Gas manager instance
            session_factory: Optional async session factory for distributed locking
        """
        self.usdt_contract_address = to_checksum_address(usdt_contract_address)
        self.wallet_account = wallet_account
        self.wallet_address = wallet_address
        self.gas_manager = gas_manager
        self.session_factory = session_factory

        # Nonce lock for preventing race conditions in parallel transactions
        self._nonce_lock = asyncio.Lock()

    def _get_safe_nonce(self, w3: Web3, address: str) -> int:
        """
        Get nonce with stuck transaction detection.

        SYNC method - runs in executor.

        Args:
            w3: Web3 instance
            address: Wallet address

        Returns:
            Safe nonce to use
        """
        # Get pending nonce (includes pending transactions)
        pending_nonce = w3.eth.get_transaction_count(address, 'pending')
        # Get confirmed nonce (only confirmed transactions)
        confirmed_nonce = w3.eth.get_transaction_count(address, 'latest')

        # If there are too many stuck transactions (pending > confirmed + threshold)
        if pending_nonce > confirmed_nonce + NONCE_STUCK_THRESHOLD:
            logger.warning(
                f"Possible stuck transactions detected: "
                f"pending={pending_nonce}, confirmed={confirmed_nonce}, "
                f"stuck={pending_nonce - confirmed_nonce}"
            )

        return pending_nonce

    async def _get_nonce_with_distributed_lock(
        self,
        w3: Web3,
        address: str,
        executor: Any,
    ) -> int:
        """
        Get nonce with distributed lock for multi-instance protection.

        Uses Redis-based distributed lock to prevent nonce conflicts
        when multiple bot instances are running.

        Args:
            w3: Web3 instance
            address: Wallet address
            executor: Thread pool executor

        Returns:
            Safe nonce to use
        """
        from app.utils.distributed_lock import get_distributed_lock

        # Create lock key specific to this address
        lock_key = f"nonce_lock:{address}"

        # Try to get distributed lock with Redis
        # If Redis is unavailable, fallback to PostgreSQL or local lock
        if self.session_factory:
            async with self.session_factory() as session:
                distributed_lock = get_distributed_lock(session=session)

                # Acquire distributed lock with timeout
                async with distributed_lock.lock(
                    key=lock_key,
                    timeout=30,  # Lock expires after 30 seconds
                    blocking=True,
                    blocking_timeout=10.0  # Wait max 10 seconds for lock
                ):
                    # Get nonce inside the lock
                    loop = asyncio.get_event_loop()
                    nonce = await loop.run_in_executor(
                        executor,
                        lambda: self._get_safe_nonce(w3, address)
                    )
                    return nonce
        else:
            # Fallback to local lock if no session factory
            logger.warning("No session factory available, using local lock only")
            loop = asyncio.get_event_loop()
            nonce = await loop.run_in_executor(
                executor,
                lambda: self._get_safe_nonce(w3, address)
            )
            return nonce

    async def send_usdt_payment(
        self,
        w3: Web3,
        to_address: str,
        amount: Decimal,
        executor: Any,
    ) -> dict[str, Any]:
        """
        Send USDT payment.

        Args:
            w3: Web3 instance
            to_address: Recipient wallet address
            amount: Amount in USDT (Decimal for precision)
            executor: Thread pool executor

        Returns:
            Dict with success, tx_hash, error
        """
        try:
            if not self.wallet_account:
                return {"success": False, "error": "Wallet not configured"}

            to_address = to_checksum_address(to_address)
            # Convert Decimal to wei using proper precision handling
            amount_wei = int(
                (Decimal(str(amount)) * Decimal(10 ** USDT_DECIMALS))
                .to_integral_value(ROUND_DOWN)
            )

            # Get nonce with async lock BEFORE entering executor
            # This prevents race conditions in parallel transactions
            async with self._nonce_lock:
                nonce = await self._get_nonce_with_distributed_lock(
                    w3, self.wallet_address, executor
                )

                # Now execute transaction with pre-acquired nonce
                def _send_tx(w3: Web3, nonce: int):
                    contract = w3.eth.contract(
                        address=self.usdt_contract_address, abi=USDT_ABI
                    )
                    func = contract.functions.transfer(to_address, amount_wei)

                    # Use Smart Gas
                    gas_price = self.gas_manager.get_optimal_gas_price(w3)

                    try:
                        gas_est = func.estimate_gas({"from": self.wallet_address})
                    except (Web3Exception, ContractLogicError) as e:
                        logger.warning(f"Gas estimation failed: {e}")
                        gas_est = 100000  # Fallback for USDT transfer

                    txn = func.build_transaction({
                        "from": self.wallet_address,
                        "gas": int(gas_est * GAS_LIMIT_MULTIPLIER),
                        "gasPrice": gas_price,
                        "nonce": nonce,
                        "chainId": w3.eth.chain_id,
                    })

                    logger.info(
                        f"Sending USDT tx: to={mask_address(to_address)}, amount={amount}, "
                        f"nonce={nonce}, gas_price={gas_price} wei ({gas_price / 10**9} Gwei), "
                        f"gas_limit={int(gas_est * GAS_LIMIT_MULTIPLIER)}"
                    )

                    signed = self.wallet_account.sign_transaction(txn)
                    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                    return tx_hash.hex()

                # Execute with pre-acquired nonce
                loop = asyncio.get_event_loop()
                tx_hash_str = await loop.run_in_executor(
                    executor, lambda: _send_tx(w3, nonce)
                )

            logger.info(
                f"USDT payment sent: {amount} to {mask_address(to_address)}, "
                f"hash: {mask_tx_hash(tx_hash_str)}"
            )
            return {"success": True, "tx_hash": tx_hash_str, "error": None}

        except Exception as e:
            logger.error(f"Failed to send payment: {e}")
            return {"success": False, "error": str(e)}

    async def send_native_token(
        self,
        w3: Web3,
        to_address: str,
        amount: Decimal,
        executor: Any,
    ) -> dict[str, Any]:
        """
        Send native token (BNB) to address.

        Args:
            w3: Web3 instance
            to_address: Recipient wallet address
            amount: Amount in BNB (Decimal for precision)
            executor: Thread pool executor

        Returns:
            Dict with success, tx_hash, error
        """
        try:
            if not self.wallet_account:
                return {"success": False, "error": "Wallet not configured"}

            to_address = to_checksum_address(to_address)
            # Convert Decimal to wei using proper precision handling
            amount_wei = int(
                (Decimal(str(amount)) * Decimal(10 ** 18)).to_integral_value(ROUND_DOWN)
            )

            # Get nonce with async lock BEFORE entering executor
            # This prevents race conditions in parallel transactions
            async with self._nonce_lock:
                nonce = await self._get_nonce_with_distributed_lock(
                    w3, self.wallet_address, executor
                )

                # Now execute transaction with pre-acquired nonce
                def _send_native(w3: Web3, nonce: int):
                    # Use Smart Gas
                    gas_price = self.gas_manager.get_optimal_gas_price(w3)
                    gas_limit = DEFAULT_NATIVE_GAS_LIMIT  # Standard native transfer gas

                    txn = {
                        "to": to_address,
                        "value": amount_wei,
                        "gas": gas_limit,
                        "gasPrice": gas_price,
                        "nonce": nonce,
                        "chainId": w3.eth.chain_id,
                    }

                    logger.info(
                        f"Sending BNB tx: to={mask_address(to_address)}, amount={amount}, "
                        f"nonce={nonce}, gas_price={gas_price} wei ({gas_price / 10**9} Gwei)"
                    )

                    signed = self.wallet_account.sign_transaction(txn)
                    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                    return tx_hash.hex()

                # Execute with pre-acquired nonce
                loop = asyncio.get_event_loop()
                tx_hash_str = await loop.run_in_executor(
                    executor, lambda: _send_native(w3, nonce)
                )

            logger.info(
                f"BNB payment sent: {amount} to {mask_address(to_address)}, "
                f"hash: {mask_tx_hash(tx_hash_str)}"
            )
            return {"success": True, "tx_hash": tx_hash_str, "error": None}

        except Exception as e:
            logger.error(f"Failed to send BNB: {e}")
            return {"success": False, "error": str(e)}

    def check_transaction_status_sync(self, w3: Web3, tx_hash: str) -> dict[str, Any]:
        """
        Check transaction status (sync method for executor).

        Args:
            w3: Web3 instance
            tx_hash: Transaction hash

        Returns:
            Dict with status, confirmations, block_number
        """
        try:
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                current = w3.eth.block_number
            except Web3Exception as e:
                logger.debug(f"Could not get transaction receipt: {e}")
                return {"status": "pending", "confirmations": 0}

            if not receipt:
                return {"status": "pending", "confirmations": 0}

            confirmations = max(0, current - receipt.blockNumber)
            status = "confirmed" if receipt.status == 1 else "failed"

            return {
                "status": status,
                "confirmations": confirmations,
                "block_number": receipt.blockNumber
            }
        except (TimeoutError, Web3Exception) as e:
            logger.warning(f"Failed to check transaction status: {e}")
            return {"status": "unknown", "confirmations": 0}

    def fetch_transaction_details_sync(self, w3: Web3, tx_hash: str) -> dict[str, Any] | None:
        """
        Fetch transaction details (sync method for executor).

        Args:
            w3: Web3 instance
            tx_hash: Transaction hash

        Returns:
            Dict with transaction details or None on error
        """
        try:
            tx = w3.eth.get_transaction(tx_hash)
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
            except Web3Exception as e:
                logger.debug(f"Could not get transaction receipt: {e}")
                receipt = None

            # Parse logic...
            contract = w3.eth.contract(address=self.usdt_contract_address, abi=USDT_ABI)

            from_address = to_checksum_address(tx["from"])
            to_address = to_checksum_address(tx["to"]) if tx["to"] else None
            value = Decimal(0)

            if to_address and to_address.lower() == self.usdt_contract_address.lower():
                try:
                    decoded = contract.decode_function_input(tx["input"])
                    if decoded[0].fn_name == "transfer":
                        amount_wei = decoded[1]["_value"]
                        value = Decimal(amount_wei) / Decimal(10 ** USDT_DECIMALS)
                        to_address = to_checksum_address(decoded[1]["_to"])
                except Exception:
                    pass

            return {
                "from_address": from_address,
                "to_address": to_address,
                "value": value,
                "status": "confirmed" if receipt and receipt.status == 1 else "pending",
            }
        except (Web3Exception, ValueError) as e:
            logger.debug(f"Could not fetch transaction details: {e}")
            return None
