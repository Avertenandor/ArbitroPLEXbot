"""
User-facing message templates and formatting functions.

This module contains all user-facing messages and helper functions
for formatting data in a consistent way across the bot.
"""

from decimal import Decimal
from typing import Any

# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

WELCOME_MESSAGE = (
    "👋 **Добро пожаловать в ArbitroPLEXbot!**\n\n"
    "ArbitroPLEXbot — это платформа для инвестиций в USDT на сети "
    "Binance Smart Chain (BEP-20).\n\n"
    "**Важно:**\n"
    "• Работа ведется только с сетью **BSC (BEP-20)**\n"
    "• Базовая валюта депозитов — **USDT BEP-20**\n"
    "• **Требование:** Для доступа нужен активный кролик от [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)\n\n"
    "🌐 **Официальный сайт:**\n"
    "[arbitrage-bot.com](https://arbitrage-bot.com/)\n\n"
    "Для начала работы необходимо пройти регистрацию."
)

AUTH_REQUIRED = (
    "🔐 **Требуется авторизация**\n\n"
    "Для доступа к боту необходимо пройти авторизацию.\n\n"
    "Отправьте **10 PLEX** на системный кошелек для получения доступа."
)

WALLET_PROMPT = (
    "💳 **Шаг 1: Укажите адрес кошелька**\n\n"
    "Введите ваш BSC (BEP-20) адрес кошелька:\n"
    "Формат: `0x...` (42 символа)\n\n"
    "⚠️ **КРИТИЧНО:** Указывайте только **ЛИЧНЫЙ** кошелек "
    "(Trust Wallet, MetaMask, SafePal или любой холодный кошелек).\n"
    "🚫 **НЕ указывайте** адрес биржи (Binance, Bybit), "
    "иначе выплаты могут быть утеряны!"
)

INVALID_WALLET = (
    "❌ **Неверный формат адреса!**\n\n"
    "BSC адрес должен начинаться с `0x` и содержать 42 символа "
    "(0x + 40 hex символов).\n\n"
    "Попробуйте еще раз:"
)

PAYMENT_REQUIRED = (
    "💰 **Оплата доступа**\n\n"
    "Отправьте **{amount} PLEX** на кошелек:\n"
    "`{wallet_address}`\n"
    "_(Нажмите для копирования)_\n\n"
    "📌 **Контракт PLEX:**\n"
    "`{token_address}`\n\n"
    "📱 Отсканируйте QR-код в вашем кошельке для быстрой отправки.\n\n"
    "После оплаты нажмите кнопку ниже."
)

PAYMENT_VERIFIED = (
    "✅ **Оплата подтверждена!**\n\n"
    "Транзакция: `{tx_hash}`\n"
    "Сумма: **{amount} PLEX**\n\n"
    "Ваш доступ активирован."
)

REGISTRATION_COMPLETE = (
    "🎉 **Регистрация завершена!**\n\n"
    "Ваш аккаунт успешно создан и активирован.\n"
    "Кошелек: `{wallet_address}`\n\n"
    "✅ Теперь вы можете пользоваться всеми функциями бота.\n\n"
    "Используйте главное меню для навигации."
)

MAIN_MENU_TEXT = (
    "📊 **Главное меню**\n\n"
    "Добро пожаловать, {username}!\n"
    "💰 Баланс: `{balance} USDT`\n\n"
    "Выберите действие:\n\n"
    "🐰 Партнер: [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)"
)

BALANCE_INFO_TEMPLATE = (
    "💰 **Ваш баланс:**\n\n"
    "Общий: `{total} USDT`\n"
    "Доступно: `{available} USDT`\n"
    "В ожидании: `{pending} USDT`\n\n"
    "📊 **Статистика:**\n"
    "Депозиты: `{deposits} USDT`\n"
    "Выводы: `{withdrawals} USDT`\n"
    "Заработано: `{earnings} USDT`"
)

DEPOSIT_INFO_TEMPLATE = (
    "💰 **Информация о депозите**\n\n"
    "📍 Уровень: **{level}**\n"
    "💵 Сумма: `{amount} USDT`\n"
    "📊 Статус: {status}\n"
    "📅 Дата создания: {created_at}\n\n"
    "📈 **ROI Прогресс:**\n"
    "{progress_bar} {progress}%\n"
    "✅ Получено: `{roi_paid} USDT`\n"
    "⏳ Осталось: `{roi_remaining} USDT`\n"
    "🎯 Цель: `{roi_cap} USDT` (500%)"
)


# ============================================================================
# FORMAT FUNCTIONS
# ============================================================================

def format_balance(balance: Decimal, pending: Decimal) -> str:
    """
    Format balance information for display.

    Args:
        balance: Available balance amount
        pending: Pending earnings amount

    Returns:
        Formatted balance string

    Example:
        >>> format_balance(Decimal("123.45"), Decimal("10.50"))
        '💰 Доступно: `123.45 USDT`\\n⏳ В ожидании: `10.50 USDT`'
    """
    balance_float = float(balance)
    pending_float = float(pending)

    return (
        f"💰 Доступно: `{balance_float:.2f} USDT`\n"
        f"⏳ В ожидании: `{pending_float:.2f} USDT`"
    )


def format_deposit_status(deposit: Any) -> str:
    """
    Format deposit status information for display.

    Args:
        deposit: Deposit object with amount, level, status, and ROI information

    Returns:
        Formatted deposit status string

    Example:
        >>> deposit = ...  # Deposit object
        >>> format_deposit_status(deposit)
        '✅ Уровень 1: 30.00 USDT - Активен'
    """
    # Get deposit attributes safely
    level = getattr(deposit, "level", 0)
    amount = float(getattr(deposit, "amount", 0))
    is_active = getattr(deposit, "is_active", False)
    is_roi_completed = getattr(deposit, "is_roi_completed", False)

    # Determine status emoji and text
    if is_roi_completed:
        status_emoji = "🏆"
        status_text = "Закрыт (ROI 500%)"
    elif is_active:
        status_emoji = "✅"
        status_text = "Активен"
    else:
        status_emoji = "❌"
        status_text = "Неактивен"

    return f"{status_emoji} Уровень {level}: {amount:.2f} USDT - {status_text}"


def format_withdrawal_status(withdrawal: Any) -> str:
    """
    Format withdrawal status information for display.

    Args:
        withdrawal: Withdrawal object with amount, status, and timestamps

    Returns:
        Formatted withdrawal status string

    Example:
        >>> withdrawal = ...  # Withdrawal object
        >>> format_withdrawal_status(withdrawal)
        '💸 Вывод: 50.00 USDT - ⏳ В обработке'
    """
    # Get withdrawal attributes safely
    amount = float(getattr(withdrawal, "amount", 0))
    status = getattr(withdrawal, "status", "unknown")
    created_at = getattr(withdrawal, "created_at", None)

    # Map status to emoji and text
    status_map = {
        "pending": ("⏳", "В обработке"),
        "processing": ("🔄", "Обрабатывается"),
        "completed": ("✅", "Завершен"),
        "cancelled": ("❌", "Отменен"),
        "failed": ("⚠️", "Ошибка"),
    }

    status_emoji, status_text = status_map.get(
        status.lower() if isinstance(status, str) else "unknown",
        ("❓", "Неизвестно")
    )

    result = f"💸 Вывод: {amount:.2f} USDT - {status_emoji} {status_text}"

    # Add creation date if available
    if created_at:
        try:
            date_str = created_at.strftime("%d.%m.%Y %H:%M")
            result += f"\n📅 {date_str}"
        except (AttributeError, ValueError):
            pass

    return result


def format_usdt(amount: Decimal | float | int) -> str:
    """
    Format USDT amount consistently.

    Args:
        amount: Amount to format

    Returns:
        Formatted USDT amount string

    Example:
        >>> format_usdt(123.456789)
        '123.46'
        >>> format_usdt(Decimal("1000.1"))
        '1000.10'
    """
    if isinstance(amount, (Decimal, float, int)):
        return f"{float(amount):.2f}"
    return "0.00"


def format_progress_bar(progress: float, length: int = 10) -> str:
    """
    Format a progress bar for display.

    Args:
        progress: Progress percentage (0-100)
        length: Length of the progress bar in characters

    Returns:
        Progress bar string

    Example:
        >>> format_progress_bar(50.0)
        '█████░░░░░'
        >>> format_progress_bar(100.0, length=5)
        '█████'
    """
    # Ensure progress is between 0 and 100
    progress = max(0.0, min(100.0, progress))

    # Calculate filled and empty sections
    filled = int((progress / 100) * length)
    empty = length - filled

    return "█" * filled + "░" * empty


def format_wallet_short(wallet_address: str) -> str:
    """
    Format wallet address in short form.

    Args:
        wallet_address: Full wallet address

    Returns:
        Shortened wallet address

    Example:
        >>> format_wallet_short("0x1234567890abcdef1234567890abcdef12345678")
        '0x12345678...12345678'
    """
    if not wallet_address or len(wallet_address) < 20:
        return wallet_address

    return f"{wallet_address[:10]}...{wallet_address[-8:]}"


def format_transaction_hash_short(tx_hash: str) -> str:
    """
    Format transaction hash in short form.

    Args:
        tx_hash: Full transaction hash

    Returns:
        Shortened transaction hash

    Example:
        >>> format_transaction_hash_short(
        ...     "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        ... )
        '0xabcdef...567890'
    """
    if not tx_hash or len(tx_hash) < 20:
        return tx_hash

    return f"{tx_hash[:10]}...{tx_hash[-6:]}"


def escape_markdown(text: str) -> str:
    """
    Escape markdown special characters for safe display.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for Markdown

    Example:
        >>> escape_markdown("test_value")
        'test\\_value'
        >>> escape_markdown("*bold*")
        '\\*bold\\*'
    """
    if not text:
        return text

    # Escape Markdown special characters
    special_chars = ["_", "*", "`", "["]
    for char in special_chars:
        text = text.replace(char, f"\\{char}")

    return text
