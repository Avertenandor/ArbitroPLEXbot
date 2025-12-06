"""
Amount validation for deposits.

Validates deposit amounts against level requirements.
"""

from decimal import Decimal

from loguru import logger

from app.services.deposit.constants import get_level_config


class AmountValidator:
    """Validator for deposit amounts."""

    # Amount tolerance (±5% for minor blockchain rounding)
    AMOUNT_TOLERANCE_PERCENT = Decimal("0.05")  # 5%

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

        # Get required amount
        required_amount = config.amount

        # Calculate tolerance
        min_amount = required_amount * (Decimal("1") - self.AMOUNT_TOLERANCE_PERCENT)
        max_amount = required_amount * (Decimal("1") + self.AMOUNT_TOLERANCE_PERCENT)

        # Validate amount
        if amount < min_amount or amount > max_amount:
            logger.debug(
                "Amount outside corridor",
                extra={
                    "level_type": level_type,
                    "amount": float(amount),
                    "required": float(required_amount),
                    "min": float(min_amount),
                    "max": float(max_amount),
                },
            )
            return (
                False,
                f"Сумма должна быть {required_amount} USDT "
                f"(допустимо: {min_amount:.2f} - {max_amount:.2f} USDT)",
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

        required_amount = config.amount
        min_amount = required_amount * (Decimal("1") - self.AMOUNT_TOLERANCE_PERCENT)
        max_amount = required_amount * (Decimal("1") + self.AMOUNT_TOLERANCE_PERCENT)

        return {
            "level_type": level_type,
            "display_name": config.display_name,
            "required_amount": required_amount,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "tolerance_percent": self.AMOUNT_TOLERANCE_PERCENT * 100,
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
