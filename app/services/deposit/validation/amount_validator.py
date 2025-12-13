"""
Amount validation for deposits.

Validates deposit amounts against level requirements.
"""

from decimal import Decimal

from loguru import logger

from app.services.deposit.constants import get_level_config


class AmountValidator:
    """Validator for deposit amounts."""

    def validate_amount_in_corridor(
        self, level_type: str, amount: Decimal
    ) -> tuple[bool, str | None]:
        """
        Validate that amount is within acceptable corridor for level.

        Args:
            level_type: Level type (e.g., "test", "level_1")
            amount: Deposit amount in USDT

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get level configuration
        config = get_level_config(level_type)
        if not config:
            return False, f"Неверный уровень: {level_type}"

        # Get min/max from configuration
        min_amount = config.min_amount
        max_amount = config.max_amount

        # Validate amount is within corridor
        if amount < min_amount or amount > max_amount:
            logger.debug(
                "Amount outside corridor",
                extra={
                    "level_type": level_type,
                    "amount": float(amount),
                    "min": float(min_amount),
                    "max": float(max_amount),
                },
            )
            return (
                False,
                f"Сумма должна быть в диапазоне "
                f"{min_amount:.2f} - {max_amount:.2f} USDT",
            )

        return True, None

    def get_corridor_info(self, level_type: str) -> dict | None:
        """
        Get corridor information for a level.

        Args:
            level_type: Level type (e.g., "test", "level_1")

        Returns:
            Dictionary with corridor info or None if level not found
        """
        config = get_level_config(level_type)
        if not config:
            return None

        return {
            "level_type": level_type,
            "display_name": config.display_name,
            "min_amount": config.min_amount,
            "max_amount": config.max_amount,
        }

    def validate_amount_positive(
        self, amount: Decimal
    ) -> tuple[bool, str | None]:
        """
        Validate that amount is positive.

        Args:
            amount: Deposit amount

        Returns:
            Tuple of (is_valid, error_message)
        """
        if amount <= 0:
            return False, "Сумма должна быть положительной"
        return True, None
