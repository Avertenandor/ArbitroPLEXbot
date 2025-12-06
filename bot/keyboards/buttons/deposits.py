"""Deposit-related button constants."""


class DepositButtons:
    """Deposit-related buttons."""

    # Deposit level status prefixes (for dynamic buttons)
    ACTIVE_PREFIX = "✅"
    LOCKED_PREFIX = "🔒"
    AVAILABLE_PREFIX = "💰"

    # Static buttons
    CHANGE_WALLET = "🔄 Сменить кошелек"

    # Template for level buttons (to be formatted)
    @staticmethod
    def level_button(level: int, amount: int, status: str = "available") -> str:
        """Generate deposit level button text."""
        if status == "active":
            return f"✅ Level {level} ({amount} USDT) - Активен"
        elif status == "locked_no_prev":
            return f"🔒 Level {level} ({amount} USDT) - Нет предыдущего"
        elif status == "locked_closed":
            return f"🔒 Level {level} ({amount} USDT) - Закрыт"
        elif status == "locked_unavailable":
            return f"🔒 Level {level} ({amount} USDT) - Недоступен"
        else:  # available
            return f"💰 Пополнить Level {level} ({amount} USDT)"
