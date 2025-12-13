"""
Withdrawal lifecycle handling module.

Handles withdrawal approval, rejection, cancellation, and escrow-based
dual-control approval processes.
"""

from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.repositories.admin_action_escrow_repository import (
    AdminActionEscrowRepository,
)
from app.repositories.transaction_repository import TransactionRepository
from app.services.withdrawal.withdrawal_balance_manager import (
    WithdrawalBalanceManager,
)


class WithdrawalLifecycleHandler:
    """Handles withdrawal lifecycle operations."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize withdrawal lifecycle handler.

        Args:
            session: Database session
        """
        self.session = session
        self.transaction_repo = TransactionRepository(session)
        self.balance_manager = WithdrawalBalanceManager(session)

    async def cancel_withdrawal(
        self, transaction_id: int, user_id: int
    ) -> tuple[bool, str | None]:
        """
        Cancel withdrawal and RETURN BALANCE to user.

        Args:
            transaction_id: Transaction ID
            user_id: User ID (for authorization)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get transaction with lock
            stmt_tx = select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.WITHDRAWAL.value,
                Transaction.status == TransactionStatus.PENDING.value,
            ).with_for_update()

            result_tx = await self.session.execute(stmt_tx)
            transaction = result_tx.scalar_one_or_none()

            if not transaction:
                return False, "Заявка не найдена или не может быть отменена"

            # CRITICAL: Return balance to user using balance manager
            success = await self.balance_manager.restore_balance(
                user_id, transaction.amount, transaction_id
            )

            if not success:
                await self.session.rollback()
                return False, "Ошибка возврата баланса"

            # Update transaction status
            transaction.status = TransactionStatus.FAILED.value

            await self.session.commit()

            logger.info(
                "Withdrawal cancelled and balance returned",
                extra={
                    "transaction_id": transaction_id,
                    "user_id": user_id,
                    "amount": str(transaction.amount),
                },
            )

            return True, None

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Failed to cancel withdrawal",
                extra={
                    "transaction_id": transaction_id,
                    "user_id": user_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return False, "Ошибка отмены заявки"

    async def approve_withdrawal(
        self,
        transaction_id: int,
        tx_hash: str,
        admin_id: int | None = None,
    ) -> tuple[bool, str | None]:
        """
        Approve withdrawal (admin only).

        R18-4: This method is called after dual control is completed
        (escrow approved by second admin) or for small withdrawals.

        Args:
            transaction_id: Transaction ID
            tx_hash: Blockchain transaction hash
            admin_id: Admin ID (for logging)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            stmt = select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.type == TransactionType.WITHDRAWAL.value,
                # Can approve PENDING or PROCESSING (if auto-withdrawal failed or stuck)
                Transaction.status.in_([TransactionStatus.PENDING.value, TransactionStatus.PROCESSING.value]),
            ).with_for_update()

            result = await self.session.execute(stmt)
            withdrawal = result.scalar_one_or_none()

            if not withdrawal:
                return (
                    False,
                    "Заявка на вывод не найдена или уже обработана",
                )

            # Update withdrawal status to PROCESSING (or COMPLETED? Logic says approve means we HAVE tx_hash)
            # If we pass tx_hash, it means it is DONE (or submitted).
            # Usually approve_withdrawal marks it as PROCESSING, and blockchain callback marks as COMPLETED.
            # But here we pass tx_hash, so it means it was sent.

            # Let's keep it PROCESSING for now, background job will check receipt.
            withdrawal.status = TransactionStatus.PROCESSING.value
            withdrawal.tx_hash = tx_hash
            await self.session.commit()

            logger.info(
                "Withdrawal approved/updated with tx_hash",
                extra={
                    "transaction_id": transaction_id,
                    "user_id": withdrawal.user_id,
                    "amount": str(withdrawal.amount),
                    "tx_hash": tx_hash,
                    "admin_id": admin_id,
                },
            )

            return True, None

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Failed to approve withdrawal",
                extra={
                    "transaction_id": transaction_id,
                    "tx_hash": tx_hash,
                    "admin_id": admin_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return False, "Ошибка подтверждения заявки"

    async def approve_withdrawal_via_escrow(
        self,
        escrow_id: int,
        approver_admin_id: int,
        blockchain_service: Any,
    ) -> tuple[bool, str | None, str | None]:
        """
        Approve withdrawal via escrow (second admin).

        This implements dual-control where a second admin must approve
        large withdrawals initiated by the first admin.

        Args:
            escrow_id: Escrow ID
            approver_admin_id: Second admin ID
            blockchain_service: Blockchain service instance

        Returns:
            Tuple of (success, error_message, tx_hash)
        """
        try:
            escrow_repo = AdminActionEscrowRepository(self.session)
            escrow = await escrow_repo.get_by_id(escrow_id)

            if not escrow:
                return False, "Escrow не найден", None

            if escrow.status != "PENDING":
                return False, f"Escrow уже обработан (статус: {escrow.status})", None

            if escrow.operation_type != "WITHDRAWAL_APPROVAL":
                return False, "Неподдерживаемый тип операции", None

            if escrow.initiator_admin_id == approver_admin_id:
                return False, "Нельзя одобрить собственную инициацию", None

            transaction_id = escrow.operation_data.get("transaction_id")
            Decimal(str(escrow.operation_data.get("amount", 0)))
            to_address = escrow.operation_data.get("to_address")

            if not transaction_id or not to_address:
                return False, "Неверные данные в escrow", None

            if settings.blockchain_maintenance_mode:
                return False, "Blockchain в режиме обслуживания", None

            # Get withdrawal transaction to retrieve fee
            withdrawal = await self.get_withdrawal_by_id(transaction_id)
            if not withdrawal:
                return False, "Транзакция не найдена", None

            # CRITICAL: Send net_amount (amount - fee) to user, not gross amount
            net_amount = withdrawal.amount - withdrawal.fee
            payment_result = await blockchain_service.send_payment(
                to_address, net_amount
            )

            if not payment_result["success"]:
                error_msg = payment_result.get("error", "Неизвестная ошибка")
                return False, f"Ошибка отправки в блокчейн: {error_msg}", None

            tx_hash = payment_result["tx_hash"]

            approved_escrow = await escrow_repo.approve(escrow_id, approver_admin_id)

            if not approved_escrow:
                return False, "Ошибка при подтверждении escrow", None

            success, error_msg = await self.approve_withdrawal(
                transaction_id, tx_hash, approver_admin_id
            )

            if not success:
                await self.session.rollback()
                return False, error_msg or "Ошибка при одобрении вывода", None

            await self.session.commit()

            return True, None, tx_hash

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Failed to approve withdrawal via escrow",
                extra={
                    "escrow_id": escrow_id,
                    "approver_admin_id": approver_admin_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return False, f"Ошибка при одобрении через escrow: {str(e)}", None

    async def reject_withdrawal(
        self, transaction_id: int, reason: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Reject withdrawal and RETURN BALANCE.

        Args:
            transaction_id: Transaction ID
            reason: Rejection reason (optional)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            stmt_tx = select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.type == TransactionType.WITHDRAWAL.value,
                Transaction.status == TransactionStatus.PENDING.value,
            ).with_for_update()

            result_tx = await self.session.execute(stmt_tx)
            withdrawal = result_tx.scalar_one_or_none()

            if not withdrawal:
                return (False, "Заявка на вывод не найдена или уже обработана")

            # CRITICAL: Return balance to user using balance manager
            success = await self.balance_manager.restore_balance(
                withdrawal.user_id, withdrawal.amount, transaction_id
            )

            if not success:
                await self.session.rollback()
                return False, "Ошибка возврата баланса"

            withdrawal.status = TransactionStatus.FAILED.value
            await self.session.commit()

            logger.info(
                "Withdrawal rejected and balance returned",
                extra={
                    "transaction_id": transaction_id,
                    "user_id": withdrawal.user_id,
                    "amount": str(withdrawal.amount),
                    "reason": reason,
                },
            )

            return True, None

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                "Failed to reject withdrawal",
                extra={
                    "transaction_id": transaction_id,
                    "reason": reason,
                    "error": str(e),
                },
                exc_info=True,
            )
            return False, "Ошибка отклонения заявки"

    async def get_withdrawal_by_id(
        self, transaction_id: int
    ) -> Transaction | None:
        """
        Get withdrawal by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction or None if not found
        """
        stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
