"""
Withdrawal security checks module.

Contains security-related validation checks:
- Finpass recovery checks
- Fraud detection checks
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


class SecurityChecksMixin:
    """Mixin providing security-related validation checks."""

    session: AsyncSession

    async def check_finpass_recovery(
        self, user_id: int
    ) -> tuple[bool, str | None]:
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
            logger.warning(
                f"Withdrawal blocked: User {user_id} "
                f"has active finpass recovery"
            )
            return False, (
                "Вывод средств временно заблокирован "
                "из-за активного процесса восстановления "
                "финансового пароля. "
                "Дождитесь завершения процедуры восстановления."
            )

        return True, None

    async def check_fraud_detection(
        self, user_id: int
    ) -> tuple[bool, str | None]:
        """
        Check if user has fraud risk.

        Args:
            user_id: User ID

        Returns:
            Tuple of (is_valid, error_message)
        """
        from app.services.fraud_detection_service import (
            FraudDetectionService,
        )

        fraud_service = FraudDetectionService(self.session)
        fraud_check = await fraud_service.check_and_block_if_needed(
            user_id
        )

        if fraud_check.get("blocked"):
            logger.warning(
                f"Withdrawal blocked: User {user_id} "
                f"flagged by fraud detection"
            )
            error_msg = (
                "Вывод средств временно заблокирован "
                "из-за подозрительной активности. "
                "Обратитесь в поддержку."
            )
            return False, error_msg

        return True, None
