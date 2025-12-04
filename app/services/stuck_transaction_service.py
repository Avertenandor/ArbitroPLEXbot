"""
Stuck Transaction Service (R7-6).

Monitors and handles stuck withdrawal transactions.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3.exceptions import TransactionNotFound

from app.config.constants import BLOCKCHAIN_TIMEOUT
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.transaction_repository import TransactionRepository
from app.services.user_service import UserService


class StuckTransactionService:
    """Service for monitoring and handling stuck transactions."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize stuck transaction service."""
        self.session = session
        self.transaction_repo = TransactionRepository(session)
        self.user_service = UserService(session)

    async def find_stuck_withdrawals(
        self, older_than_minutes: int = 15
    ) -> list[Transaction]:
        """
        Find withdrawal transactions in PROCESSING status older than threshold.

        Args:
            older_than_minutes: Minimum age in minutes to consider stuck

        Returns:
            List of stuck withdrawal transactions
        """
        threshold = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
        # Convert to naive datetime (UTC) to match Transaction model's naive DateTime column
        # This avoids "can't subtract offset-naive and offset-aware datetimes" error in asyncpg
        threshold_naive = threshold.replace(tzinfo=None)

        stmt = (
            select(Transaction)
            .where(
                Transaction.type == TransactionType.WITHDRAWAL.value,
                Transaction.status == TransactionStatus.PROCESSING.value,
                Transaction.tx_hash.isnot(None),
                Transaction.updated_at < threshold_naive,
            )
            .order_by(Transaction.updated_at.asc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def check_transaction_status(
        self, tx_hash: str, web3
    ) -> dict[str, Any]:
        """
        Check transaction status in blockchain.

        Args:
            tx_hash: Transaction hash
            web3: Web3 instance

        Returns:
            Dict with status, receipt, error
        """
        try:
            # Try to get transaction receipt with timeout
            try:
                receipt = await asyncio.wait_for(
                    web3.eth.get_transaction_receipt(tx_hash),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except TimeoutError:
                logger.error(f"Timeout getting transaction receipt for {tx_hash}")
                return {
                    "status": "error",
                    "error": "Timeout",
                    "receipt": None,
                }
            except TransactionNotFound:
                # Transaction not mined yet - check if it's in mempool with timeout
                try:
                    tx = await asyncio.wait_for(
                        web3.eth.get_transaction(tx_hash),
                        timeout=BLOCKCHAIN_TIMEOUT,
                    )
                    if tx:
                        return {
                            "status": "pending",
                            "in_mempool": True,
                            "receipt": None,
                        }
                except TimeoutError:
                    logger.error(f"Timeout checking transaction in mempool {tx_hash}")
                    return {
                        "status": "error",
                        "error": "Timeout",
                        "receipt": None,
                    }
                except TransactionNotFound:
                    pass

                return {
                    "status": "not_found",
                    "in_mempool": False,
                    "receipt": None,
                }

            # Transaction has receipt
            if receipt["status"] == 1:
                return {
                    "status": "confirmed",
                    "in_mempool": False,
                    "receipt": receipt,
                    "block_number": receipt["blockNumber"],
                }
            else:
                return {
                    "status": "failed",
                    "in_mempool": False,
                    "receipt": receipt,
                    "error": "Transaction reverted",
                }

        except Exception as e:
            logger.error(f"Error checking transaction {tx_hash}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "receipt": None,
            }

    def _handle_confirmed_status(self, withdrawal: Transaction) -> dict[str, Any]:
        """Handle confirmed transaction status."""
        withdrawal.status = TransactionStatus.CONFIRMED.value
        logger.info(
            f"Stuck transaction {withdrawal.id} confirmed",
            extra={
                "transaction_id": withdrawal.id,
                "tx_hash": withdrawal.tx_hash,
            },
        )
        return {"action": "confirmed", "success": True}

    async def _handle_failed_status(self, withdrawal: Transaction) -> dict[str, Any]:
        """Handle failed transaction status and refund user."""
        try:
            # Get user with lock
            stmt = (
                select(User)
                .where(User.id == withdrawal.user_id)
                .with_for_update()
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.balance = user.balance + withdrawal.amount

            withdrawal.status = TransactionStatus.FAILED.value

            logger.warning(
                f"Stuck transaction {withdrawal.id} failed, funds returned to user",
                extra={
                    "transaction_id": withdrawal.id,
                    "tx_hash": withdrawal.tx_hash,
                    "user_id": withdrawal.user_id,
                    "amount": str(withdrawal.amount),
                },
            )

            return {"action": "failed_refunded", "success": True}

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error handling failed transaction {withdrawal.id}: {e}")
            return {
                "action": "failed_refund_error",
                "success": False,
                "error": str(e),
            }

    async def _handle_pending_status(self, withdrawal: Transaction, web3) -> dict[str, Any]:
        """Handle pending transaction status and check for speed-up."""
        try:
            tx = await self._get_transaction_with_timeout(withdrawal.tx_hash, web3)
            if tx is None:
                return {"action": "pending_no_tx", "success": False}

            current_gas_price = await self._get_gas_price_with_timeout(web3)
            if current_gas_price is None:
                return {
                    "action": "pending_gas_price_timeout",
                    "success": False,
                    "error": "Timeout",
                }

            tx_gas_price = tx.get("gasPrice", 0)

            if tx_gas_price < current_gas_price:
                new_gas_price = int(current_gas_price * 1.2)
                logger.info(
                    f"Attempting speed-up for transaction {withdrawal.tx_hash}: "
                    f"old gas {tx_gas_price}, new gas {new_gas_price}",
                )
                return {
                    "action": "pending_speedup_needed",
                    "success": False,
                    "current_gas": tx_gas_price,
                    "recommended_gas": new_gas_price,
                }

            return {"action": "pending_waiting", "success": False}

        except Exception as e:
            logger.error(
                f"Error checking pending transaction {withdrawal.tx_hash}: {e}"
            )
            return {
                "action": "pending_check_error",
                "success": False,
                "error": str(e),
            }

    async def _get_transaction_with_timeout(self, tx_hash: str, web3):
        """Get transaction with timeout handling."""
        try:
            return await asyncio.wait_for(
                web3.eth.get_transaction(tx_hash),
                timeout=BLOCKCHAIN_TIMEOUT,
            )
        except TimeoutError:
            logger.error(f"Timeout getting transaction {tx_hash}")
            return None

    async def _get_gas_price_with_timeout(self, web3):
        """Get gas price with timeout handling."""
        try:
            return await asyncio.wait_for(
                web3.eth.gas_price,
                timeout=BLOCKCHAIN_TIMEOUT,
            )
        except TimeoutError:
            logger.error("Timeout getting gas price")
            return None

    def _handle_not_found_status(self, withdrawal: Transaction) -> dict[str, Any]:
        """Handle not found transaction status."""
        logger.warning(
            f"Transaction {withdrawal.tx_hash} not found, might be dropped",
            extra={
                "transaction_id": withdrawal.id,
                "tx_hash": withdrawal.tx_hash,
            },
        )
        return {"action": "not_found_retry_needed", "success": False}

    def _handle_error_status(self, withdrawal: Transaction, tx_status: dict) -> dict[str, Any]:
        """Handle error transaction status."""
        logger.error(
            f"Error status for transaction {withdrawal.tx_hash}: "
            f"{tx_status.get('error')}",
        )
        return {
            "action": "error",
            "success": False,
            "error": tx_status.get("error"),
        }

    async def handle_stuck_transaction(
        self,
        withdrawal: Transaction,
        tx_status: dict[str, Any],
        web3,
    ) -> dict[str, Any]:
        """
        Handle stuck transaction based on its status.

        Args:
            withdrawal: Withdrawal transaction
            tx_status: Transaction status from blockchain
            web3: Web3 instance

        Returns:
            Dict with action taken and result
        """
        status = tx_status.get("status")

        if status == "confirmed":
            result = self._handle_confirmed_status(withdrawal)
            await self.session.commit()
            return result

        if status == "failed":
            result = await self._handle_failed_status(withdrawal)
            if result["success"]:
                await self.session.commit()
            return result

        if status == "pending":
            return await self._handle_pending_status(withdrawal, web3)

        if status == "not_found":
            return self._handle_not_found_status(withdrawal)

        return self._handle_error_status(withdrawal, tx_status)
