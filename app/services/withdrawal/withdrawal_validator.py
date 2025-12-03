"""
Withdrawal validation service.

Handles all validation logic for withdrawal requests.
"""

from dataclasses import dataclass
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.global_settings import GlobalSettings
from app.models.user import User
from app.repositories.deposit_repository import DepositRepository
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from app.repositories.transaction_repository import TransactionRepository


@dataclass
class ValidationResult:
    """Result of withdrawal validation."""

    is_valid: bool
    error_message: str | None = None
    error_code: str | None = None

    @classmethod
    def success(cls) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(is_valid=True)

    @classmethod
    def error(cls, message: str, code: str | None = None) -> "ValidationResult":
        """Create an error validation result."""
        return cls(is_valid=False, error_message=message, error_code=code)


class WithdrawalValidator:
    """Validator for withdrawal requests."""

    def __init__(self, session: AsyncSession, global_settings: GlobalSettings) -> None:
        """
        Initialize withdrawal validator.

        Args:
            session: Database session
            global_settings: Global settings instance
        """
        self.session = session
        self.global_settings = global_settings
        self.settings_repo = GlobalSettingsRepository(session)
        self.transaction_repo = TransactionRepository(session)

    async def validate_withdrawal_request(
        self, user_id: int, amount: Decimal, available_balance: Decimal
    ) -> ValidationResult:
        """
        Run all validations and return result.

        Args:
            user_id: User ID
            amount: Withdrawal amount
            available_balance: User's available balance

        Returns:
            ValidationResult with is_valid and optional error_message/error_code
        """
        # 1. Check emergency stop
        is_valid, error_msg = await self.check_emergency_stop()
        if not is_valid:
            return ValidationResult.error(error_msg, "EMERGENCY_STOP")

        # 2. Check minimum amount
        is_valid, error_msg = await self.check_min_amount(amount)
        if not is_valid:
            return ValidationResult.error(error_msg, "MIN_AMOUNT")

        # 3. Check user status (banned, withdrawal blocked)
        is_valid, error_msg = await self.check_user_banned(user_id)
        if not is_valid:
            return ValidationResult.error(error_msg, "USER_BANNED")

        # 4. Check finpass recovery
        is_valid, error_msg = await self.check_finpass_recovery(user_id)
        if not is_valid:
            return ValidationResult.error(error_msg, "FINPASS_RECOVERY")

        # 5. Check fraud detection
        is_valid, error_msg = await self.check_fraud_detection(user_id)
        if not is_valid:
            return ValidationResult.error(error_msg, "FRAUD_DETECTION")

        # 6. Check balance
        is_valid, error_msg = await self.check_balance(user_id, amount, available_balance)
        if not is_valid:
            return ValidationResult.error(error_msg, "INSUFFICIENT_BALANCE")

        # 7. Check daily limit (if enabled)
        is_valid, error_msg = await self.check_daily_limit(user_id, amount)
        if not is_valid:
            return ValidationResult.error(error_msg, "DAILY_LIMIT")

        return ValidationResult.success()

    async def check_emergency_stop(self) -> tuple[bool, str | None]:
        """
        Check if emergency stop is active.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check both static config flag and DB flag
        if (
            settings.emergency_stop_withdrawals
            or getattr(self.global_settings, "emergency_stop_withdrawals", False)
        ):
            logger.warning("Withdrawal blocked by emergency stop")
            return False, (
                "⚠️ Временная приостановка выводов из-за технических работ.\n\n"
                "Ваши средства в безопасности, выводы будут доступны после "
                "восстановления.\n\n"
                "Следите за обновлениями в нашем канале."
            )
        return True, None

    async def check_user_banned(self, user_id: int) -> tuple[bool, str | None]:
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
            return False, (
                "Ваш аккаунт заблокирован. "
                "Обратитесь в поддержку для выяснения причин."
            )

        # Check if withdrawals are blocked for this user
        if user.withdrawal_blocked:
            logger.warning(f"Withdrawal blocked: User {user_id} has withdrawal_blocked=True")
            return False, (
                "Вывод средств заблокирован. "
                "Обратитесь в поддержку для выяснения причин."
            )

        return True, None

    async def check_min_amount(self, amount: Decimal) -> tuple[bool, str | None]:
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
                f"Недостаточно средств. Доступно: {available_balance:.2f} USDT"
            )

        return True, None

    async def check_daily_limit(
        self, user_id: int, amount: Decimal
    ) -> tuple[bool, str | None]:
        """
        Check if withdrawal exceeds daily limit.

        Note: Currently disabled by admin request to allow full balance withdrawal.
        This method is kept for future use if daily limits need to be re-enabled.

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

    async def check_finpass_recovery(self, user_id: int) -> tuple[bool, str | None]:
        """
        Check if user has active finpass recovery.

        Args:
            user_id: User ID

        Returns:
            Tuple of (is_valid, error_message)
        """
        from app.services.finpass_recovery_service import (
            FinpassRecoveryService,
        )

        finpass_service = FinpassRecoveryService(self.session)
        if await finpass_service.has_active_recovery(user_id):
            logger.warning(f"Withdrawal blocked: User {user_id} has active finpass recovery")
            return False, (
                "Вывод средств временно заблокирован "
                "из-за активного процесса восстановления "
                "финансового пароля. "
                "Дождитесь завершения процедуры восстановления."
            )

        return True, None

    async def check_fraud_detection(self, user_id: int) -> tuple[bool, str | None]:
        """
        Check if user has fraud risk.

        Args:
            user_id: User ID

        Returns:
            Tuple of (is_valid, error_message)
        """
        from app.services.fraud_detection_service import FraudDetectionService

        fraud_service = FraudDetectionService(self.session)
        fraud_check = await fraud_service.check_and_block_if_needed(user_id)

        if fraud_check.get("blocked"):
            logger.warning(f"Withdrawal blocked: User {user_id} flagged by fraud detection")
            return False, (
                "Вывод средств временно заблокирован "
                "из-за подозрительной активности. "
                "Обратитесь в поддержку."
            )

        return True, None

    async def check_auto_withdrawal_eligibility(
        self, user_id: int, amount: Decimal
    ) -> bool:
        """
        Check if withdrawal is eligible for auto-approval.

        Logic:
        1. Auto-withdrawal must be enabled globally.
        2. x5 Rule: (Total Withdrawn + Request) <= (Total Deposited * 5)
        3. Global Daily Limit: Today's Total + Request <= Limit (if enabled)

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

        total_withdrawn = await self.transaction_repo.get_total_withdrawn(user_id)

        if (total_withdrawn + amount) > max_payout:
            logger.info(
                f"Auto-withdrawal denied for user {user_id}: Limit x5 exceeded. "
                f"Deposited: {total_deposited}, Max Payout: {max_payout}, "
                f"Withdrawn: {total_withdrawn}, Request: {amount}"
            )
            return False

        # 2. Check Global Daily Limit (Circuit Breaker)
        if (
            self.global_settings.is_daily_limit_enabled
            and self.global_settings.daily_withdrawal_limit
        ):
            today_total = await self.transaction_repo.get_total_withdrawn_today()
            if (today_total + amount) > self.global_settings.daily_withdrawal_limit:
                logger.warning(
                    f"Auto-withdrawal denied: Global daily limit exceeded. "
                    f"Today: {today_total}, Request: {amount}, "
                    f"Limit: {self.global_settings.daily_withdrawal_limit}"
                )
                return False

        return True
