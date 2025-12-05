"""
Transaction Status Checker.

Provides functionality to check the status of blockchain transactions.
"""

import asyncio
from typing import Any

from loguru import logger
from web3 import AsyncWeb3

from app.config.constants import BLOCKCHAIN_TIMEOUT


class TransactionStatusChecker:
    """
    Checks transaction status on the blockchain.

    Features:
    - Receipt retrieval
    - Pending transaction detection
    - Timeout handling
    """

    def __init__(self, web3: AsyncWeb3):
        """
        Initialize transaction status checker.

        Args:
            web3: AsyncWeb3 instance
        """
        self.web3 = web3

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
