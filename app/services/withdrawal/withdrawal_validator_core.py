"""
Withdrawal validation core module.

Contains the main validation logic and ValidationResult class.
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.global_settings import GlobalSettings
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from app.repositories.transaction_repository import TransactionRepository
from app.services.withdrawal.withdrawal_basic_checks import (
    BasicChecksMixin,
)
from app.services.withdrawal.withdrawal_plex_checks import PlexChecksMixin
from app.services.withdrawal.withdrawal_security_checks import (
    SecurityChecksMixin,
)


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
    def error(
        cls, message: str, code: str | None = None
    ) -> "ValidationResult":
        """Create an error validation result."""
        return cls(is_valid=False, error_message=message, error_code=code)


class WithdrawalValidator(
    BasicChecksMixin, SecurityChecksMixin, PlexChecksMixin
):
    """Validator for withdrawal requests."""

    def __init__(
        self, session: AsyncSession, global_settings: GlobalSettings
    ) -> None:
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
            ValidationResult with is_valid and optional
            error_message/error_code
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
        is_valid, error_msg = await self.check_balance(
            user_id, amount, available_balance
        )
        if not is_valid:
            return ValidationResult.error(
                error_msg, "INSUFFICIENT_BALANCE"
            )

        # 7. Check PLEX daily payments for active deposits
        is_valid, error_msg = await self.check_plex_payments(user_id)
        if not is_valid:
            return ValidationResult.error(
                error_msg, "PLEX_PAYMENT_REQUIRED"
            )

        # 8. Check PLEX wallet balance (minimum 5000 PLEX required)
        is_valid, error_msg = await self.check_plex_wallet_balance(
            user_id
        )
        if not is_valid:
            return ValidationResult.error(
                error_msg, "INSUFFICIENT_PLEX_BALANCE"
            )

        # 9. Check daily limit (if enabled)
        is_valid, error_msg = await self.check_daily_limit(
            user_id, amount
        )
        if not is_valid:
            return ValidationResult.error(error_msg, "DAILY_LIMIT")

        return ValidationResult.success()
