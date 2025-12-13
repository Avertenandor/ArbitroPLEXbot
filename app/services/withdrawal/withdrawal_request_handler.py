"""
Withdrawal request handling module.

Handles the creation of withdrawal requests including validation,
balance deduction, and auto-withdrawal eligibility checks.
"""

import asyncio
import random
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.global_settings_repository import GlobalSettingsRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.withdrawal.withdrawal_balance_manager import (
    WithdrawalBalanceManager,
)
from app.services.withdrawal.withdrawal_validator import WithdrawalValidator


# R9-2: Maximum retries for race condition conflicts
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # Base delay in seconds


class WithdrawalRequestHandler:
    """Handles withdrawal request creation and validation."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize withdrawal request handler.

        Args:
            session: Database session
        """
        self.session = session
        self.transaction_repo = TransactionRepository(session)
        self.settings_repo = GlobalSettingsRepository(session)
        self.balance_manager = WithdrawalBalanceManager(session)

    async def get_min_withdrawal_amount(self) -> Decimal:
        """
        Get minimum withdrawal amount from global settings.

        Returns:
            Minimum withdrawal amount
        """
        settings = await self.settings_repo.get_settings()
        return settings.min_withdrawal_amount

    async def request_withdrawal(
        self,
        user_id: int,
        amount: Decimal,
        available_balance: Decimal,
    ) -> tuple[Transaction | None, str | None, bool]:
        """
        Request withdrawal with balance deduction.

        Args:
            user_id: User ID
            amount: Withdrawal amount
            available_balance: User's available balance

        Returns:
            Tuple of (transaction, error_message, is_auto_approved)
        """
        # Load global settings
        global_settings = await self.settings_repo.get_settings()

        # Create validator with global settings
        validator = WithdrawalValidator(self.session, global_settings)

        # Run all validations
        validation_result = await validator.validate_withdrawal_request(
            user_id, amount, available_balance
        )

        if not validation_result.is_valid:
            # If finpass recovery is active, freeze pending withdrawals
            if validation_result.error_code == "FINPASS_RECOVERY":
                from app.services.finpass_recovery_service import (
                    FinpassRecoveryService,
                )
                finpass_service = FinpassRecoveryService(self.session)
                if await finpass_service.has_active_recovery(user_id):
                    await self._freeze_pending_withdrawals(user_id)

            return None, validation_result.error_message, False

        # R9-2: Retry logic for race condition conflicts
        for attempt in range(MAX_RETRIES):
            try:
                # Get user with pessimistic lock (NOWAIT)
                stmt = (
                    select(User)
                    .where(User.id == user_id)
                    .with_for_update(nowait=True)
                )
                result = await self.session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    return None, "Пользователь не найден", False

                # Calculate Fee using balance manager
                fee_amount = await self.balance_manager.calculate_fee(amount)
                net_amount = amount - fee_amount

                # CRITICAL: Validate that fee is less than amount
                if fee_amount >= amount:
                    return None, "Комиссия превышает или равна сумме вывода", False

                # Warning: High fee detection
                if fee_amount > amount * Decimal("0.5"):
                    logger.warning(f"High fee detected: {fee_amount} is more than 50% of {amount}")

                # Deduct balance BEFORE creating transaction (Gross amount)
                # User requests 'amount', we deduct 'amount', but send 'net_amount' to blockchain
                balance_before = user.balance
                user.balance = user.balance - amount
                balance_after = user.balance

                # Check Auto-Withdrawal Eligibility
                is_auto = await validator.check_auto_withdrawal_eligibility(
                    user_id, amount
                )

                status = TransactionStatus.PROCESSING.value if is_auto else TransactionStatus.PENDING.value

                # Create withdrawal transaction
                transaction = await self.transaction_repo.create(
                    user_id=user_id,
                    type=TransactionType.WITHDRAWAL.value,
                    amount=amount,  # Gross amount
                    fee=fee_amount,  # Service fee
                    balance_before=balance_before,
                    balance_after=balance_after,
                    to_address=user.wallet_address,
                    status=status,
                )

                await self.session.commit()

                logger.info(
                    "Withdrawal request created",
                    extra={
                        "transaction_id": transaction.id,
                        "user_id": user_id,
                        "amount": str(amount),
                        "status": status,
                        "is_auto": is_auto,
                    },
                )

                return transaction, None, is_auto

            except OperationalError as e:
                # Handle lock conflict
                error_str = str(e).lower()
                if "could not obtain lock" in error_str or "lock_not_available" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 0.5)
                        await self.session.rollback()
                        await asyncio.sleep(delay)
                        continue
                    else:
                        await self.session.rollback()
                        return None, (
                            "Система временно занята. "
                            "Попробуйте через несколько секунд."
                        ), False
                else:
                    await self.session.rollback()
                    logger.error(f"Database error in withdrawal: {e}")
                    return None, "Ошибка базы данных. Попробуйте позже.", False

            except Exception as e:
                await self.session.rollback()
                logger.error(f"Failed to create withdrawal: {e}", exc_info=True)
                return None, "Ошибка создания заявки на вывод", False

    async def _freeze_pending_withdrawals(self, user_id: int) -> None:
        """
        Freeze pending withdrawals for user.

        Args:
            user_id: User ID
        """
        pending = await self.transaction_repo.get_by_user(
            user_id=user_id,
            type=TransactionType.WITHDRAWAL.value,
            status=TransactionStatus.PENDING.value,
        )

        if not pending:
            return

        for withdrawal in pending:
            # Restore balance using balance manager
            success = await self.balance_manager.restore_balance(
                user_id, withdrawal.amount, withdrawal.id
            )
            if success:
                withdrawal.status = TransactionStatus.FAILED.value

        await self.session.commit()
