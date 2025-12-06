"""
Deposit handlers utility functions.

Helper functions for deposit flow.
"""

from decimal import Decimal


def extract_level_type_from_button(text: str) -> str | None:
    """
    Extract level type from button text.

    Args:
        text: Button text like "🎯 Тестовый ($30-$100)" or "✅ Тестовый ($30-$100) - Активен"

    Returns:
        Level type (test, level_1, etc.) or None if not recognized
    """
    # Remove status indicators
    text_clean = text.replace("✅", "").replace("🔒", "").strip()

    # Map button text to level types
    level_mapping = {
        "Тестовый": "test",
        "Уровень 1": "level_1",
        "Уровень 2": "level_2",
        "Уровень 3": "level_3",
        "Уровень 4": "level_4",
        "Уровень 5": "level_5",
    }

    for name, level_type in level_mapping.items():
        if name in text_clean:
            return level_type

    return None


def format_amount(amount: Decimal) -> str:
    """
    Format amount for display.

    Args:
        amount: Amount to format

    Returns:
        Formatted string
    """
    # Remove trailing zeros
    return f"{amount:,.2f}".rstrip('0').rstrip('.')


def validate_amount_input(text: str) -> tuple[bool, Decimal | None, str | None]:
    """
    Validate amount input from user.

    Args:
        text: User input text

    Returns:
        Tuple of (is_valid, amount, error_message)
    """
    try:
        # Remove spaces and replace comma with dot
        text_clean = text.strip().replace(" ", "").replace(",", ".")

        # Try to parse as decimal
        amount = Decimal(text_clean)

        # Check if positive
        if amount <= 0:
            return False, None, "Сумма должна быть больше нуля"

        # Check if too many decimal places (max 2)
        if amount.as_tuple().exponent < -8:
            return False, None, "Слишком много знаков после запятой (максимум 8)"

        return True, amount, None

    except (ValueError, ArithmeticError):
        return False, None, "Неверный формат суммы. Используйте формат: 100 или 100.50"
