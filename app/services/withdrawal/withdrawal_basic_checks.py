"""
Withdrawal basic checks module.

Contains basic validation checks:
- Emergency stop check
- User ban check
- Minimum amount check
- Balance check
- Daily limit check
- Auto-withdrawal eligibility check
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.global_settings import GlobalSettings
from app.models.user import User
from app.repositories.deposit_repository import DepositRepository
from app.repositories.transaction_repository import TransactionRepository


class BasicChecksMixin:
    """Mixin providing basic validation checks."""

    session: AsyncSession
    global_settings: GlobalSettings
    transaction_repo: TransactionRepository

    async def check_emergency_stop(self) -> tuple[bool, str | None]:
        """
        Check if emergency stop is active.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check both static config flag and DB flag
        emergency_stop = settings.emergency_stop_withdrawals or getattr(
            self.global_settings, "emergency_stop_withdrawals", False
        )
        if emergency_stop:
            logger.warning("Withdrawal blocked by emergency stop")
            return False, (
                "⚠️ Временная приостановка выводов из-за "
                "технических работ.\n\n"
                "Ваши средства в безопасности, выводы будут доступны "
                "после восстановления.\n\n"
                "Следите за обновлениями в нашем канале."
            )
        return True, None

    async def check_user_banned(
        self, user_id: int
    ) -> tuple[bool, str | None]:
        """
        Check if user is banned or has withdrawal blocked.

        Args:
            user_id: User ID

        Returns:
            Tuple of (is_valid, error_message)
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return False, "Пользователь не найден"

        # Check if user is banned
        if user.is_banned:
            logger.warning(f"Withdrawal blocked: User {user_id} is banned")
            error_msg = (
                "Ваш аккаунт заблокирован. "
                "Обратитесь в поддержку для выяснения причин."
            )
            return False, error_msg

        # Check if withdrawals are blocked for this user
        if user.withdrawal_blocked:
            logger.warning(
                f"Withdrawal blocked: User {user_id} has "
                f"withdrawal_blocked=True"
            )
            error_msg = (
                "Вывод средств заблокирован. "
                "Обратитесь в поддержку для выяснения причин."
            )
            return False, error_msg

        return True, None

    async def check_min_amount(
        self, amount: Decimal
    ) -> tuple[bool, str | None]:
        """
        Check if withdrawal amount meets minimum requirement.

        Args:
            amount: Withdrawal amount

        Returns:
            Tuple of (is_valid, error_message)
        """
        min_amount = self.global_settings.min_withdrawal_amount

        if amount < min_amount:
            return False, f"Минимальная сумма вывода: {min_amount} USDT"

        return True, None

    async def check_balance(
        self, user_id: int, amount: Decimal, available_balance: Decimal
    ) -> tuple[bool, str | None]:
        """
        Check if user has sufficient balance.

        Args:
            user_id: User ID
            amount: Withdrawal amount
            available_balance: User's available balance

        Returns:
            Tuple of (is_valid, error_message)
        """
        if available_balance < amount:
            logger.warning(
                f"Insufficient balance for user {user_id}: "
                f"requested={amount}, available={available_balance}"
            )
            return False, (
                f"Недостаточно средств. "
                f"Доступно: {available_balance:.2f} USDT"
            )

        return True, None

    async def check_daily_limit(
        self, user_id: int, amount: Decimal
    ) -> tuple[bool, str | None]:
        """
        Check if withdrawal exceeds daily limit.

        Note: Currently disabled by admin request to allow full
        balance withdrawal. This method is kept for future use if
        daily limits need to be re-enabled.

        Args:
            user_id: User ID
            amount: Withdrawal amount

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Daily limit check is currently disabled
        # If re-enabled, implement the logic here using:
        # - self.transaction_repo.get_daily_roi(user_id)
        # - self.transaction_repo.get_total_withdrawn_today(user_id)
        return True, None

    async def check_auto_withdrawal_eligibility(
        self, user_id: int, amount: Decimal
    ) -> bool:
        """
        Check if withdrawal is eligible for auto-approval.

        Logic:
        1. Auto-withdrawal must be enabled globally.
        2. x5 Rule: (Total Withdrawn + Request) <= (Total Deposited * 5)
        3. Global Daily Limit: Today's Total + Request <= Limit
           (if enabled)

        Args:
            user_id: User ID
            amount: Withdrawal amount

        Returns:
            True if eligible for auto-approval, False otherwise
        """
        if not self.global_settings.auto_withdrawal_enabled:
            return False

        # 1. Check x5 Rule (Math Validation)
        deposit_repo = DepositRepository(self.session)
        total_deposited = await deposit_repo.get_total_deposited(user_id)

        # If no deposits, no auto withdrawal
        if total_deposited <= 0:
            return False

        max_payout = total_deposited * Decimal("5.0")

        total_withdrawn = await self.transaction_repo.get_total_withdrawn(
            user_id
        )

        if (total_withdrawn + amount) > max_payout:
            logger.info(
                f"Auto-withdrawal denied for user {user_id}: "
                f"Limit x5 exceeded. "
                f"Deposited: {total_deposited}, "
                f"Max Payout: {max_payout}, "
                f"Withdrawn: {total_withdrawn}, Request: {amount}"
            )
            return False

        # 2. Check Global Daily Limit (Circuit Breaker)
        if (
            self.global_settings.is_daily_limit_enabled
            and self.global_settings.daily_withdrawal_limit
        ):
            today_total = (
                await self.transaction_repo.get_total_withdrawn_today()
            )
            if (
                today_total + amount
            ) > self.global_settings.daily_withdrawal_limit:
                logger.warning(
                    f"Auto-withdrawal denied: "
                    f"Global daily limit exceeded. "
                    f"Today: {today_total}, Request: {amount}, "
                    f"Limit: {self.global_settings.daily_withdrawal_limit}"
                )
                return False

        return True
