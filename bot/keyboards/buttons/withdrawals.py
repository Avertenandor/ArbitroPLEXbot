"""Withdrawal-related button constants."""


class WithdrawalButtons:
    """Withdrawal-related buttons."""

    # User withdrawal
    WITHDRAW_ALL = "💸 Вывести всю сумму"
    WITHDRAW_AMOUNT = "💵 Вывести указанную сумму"
    WITHDRAWAL_HISTORY = "📜 История выводов"
    CANCEL_WITHDRAWAL = "❌ Отменить вывод"

    # Admin withdrawal
    PENDING_WITHDRAWALS = "⏳ Ожидающие выводы"
    APPROVED_WITHDRAWALS = "📋 Одобренные выводы"
    REJECTED_WITHDRAWALS = "🚫 Отклоненные выводы"
    WITHDRAWAL_SETTINGS = "⚙️ Настройки выплат"


class WithdrawalSettingsButtons:
    """Withdrawal settings buttons."""

    CHANGE_MIN_WITHDRAWAL = "💵 Изм. Мин. Вывод"
    CHANGE_DAILY_LIMIT = "🛡 Изм. Дневной Лимит"
    CHANGE_FEE = "💸 Изм. Комиссию (%)"
    DISABLE_LIMIT = "🔴 Выключить Лимит"
    ENABLE_LIMIT = "🟢 Включить Лимит"
    DISABLE_AUTO_WITHDRAWAL = "🔴 Выключить Авто-вывод"
    ENABLE_AUTO_WITHDRAWAL = "🟢 Включить Авто-вывод"
