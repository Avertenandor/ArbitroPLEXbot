"""
Deposit-specific translations for the bot.

This module contains all deposit-related translations to keep
the main translations.py file manageable.
"""

# Russian deposit translations
RU_DEPOSIT_TRANSLATIONS = {
    "deposit": {
        "scanning": "⏳ Сканируем депозиты...",
        "scanning_your_deposits": "⏳ Сканируем ваши депозиты...",
        "confirmed": "✅ **Депозит подтверждён!**",
        "user_not_found": "⚠️ Пользователь не найден. Введите /start",

        # Уровни
        "level_test": "🎯 Тестовый",
        "level_1": "💰 Уровень 1",
        "level_2": "💎 Уровень 2",
        "level_3": "🏆 Уровень 3",
        "level_4": "👑 Уровень 4",
        "level_5": "🚀 Уровень 5",

        # Коридоры
        "corridor_info": "Коридор: ${min} - ${max} USDT",
        "enter_amount": "Введите сумму депозита от ${min} до ${max} USDT:",
        "amount_below_min": "❌ Минимальная сумма: ${min} USDT",
        "amount_above_max": "❌ Максимальная сумма: ${max} USDT",

        # Статусы
        "status_active": "✅ Активен",
        "status_locked": "🔒 Недоступен",
        "status_pending": "⏳ Ожидает оплаты",

        # PLEX
        "plex_required": "Требуется PLEX: {amount} токенов/сутки",
        "plex_payment_info": "💰 Ежедневная оплата: {amount} PLEX",
        "plex_deadline": "⏰ Срок оплаты: {hours} часов",

        # Последовательность
        "need_previous_level": "🔒 Сначала откройте {level_name}",
        "level_already_active": "ℹ️ Уровень уже активен",
        "start_with_test": "👋 Начните с тестового депозита",

        # Подтверждения
        "confirm_deposit": """
📋 Подтверждение депозита

Уровень: {level_name}
Сумма: ${amount} USDT
Ежедневный PLEX: {plex_daily} токенов

Подтвердить?
        """,

        # Инструкции
        "payment_instructions": """
💳 Инструкции по оплате

1️⃣ Отправьте ${amount} USDT на адрес:
{wallet_address}

2️⃣ После подтверждения USDT, отправьте первый PLEX платёж:
{plex_amount} PLEX на тот же адрес

⚠️ Далее PLEX нужно оплачивать каждые 24 часа
        """,
    },

    "notifications": {
        "usdt_received": "✅ Получен USDT платёж: ${amount}",
        "plex_received": "✅ Получен PLEX платёж: {amount} токенов",
        "plex_reminder": "⏰ Напоминание: требуется PLEX платёж {amount} токенов",
        "plex_warning": "⚠️ ВНИМАНИЕ: Депозит будет заблокирован через {hours} часов!",
        "deposit_blocked": "❌ Депозит заблокирован за неоплату PLEX",
        "deposit_activated": "🎉 Депозит активирован! Уровень: {level_name}",
    },
}

# English deposit translations
EN_DEPOSIT_TRANSLATIONS = {
    "deposit": {
        "scanning": "⏳ Scanning deposits...",
        "scanning_your_deposits": "⏳ Scanning your deposits...",
        "confirmed": "✅ **Deposit confirmed!**",
        "user_not_found": "⚠️ User not found. Send /start",

        # Levels
        "level_test": "🎯 Test",
        "level_1": "💰 Level 1",
        "level_2": "💎 Level 2",
        "level_3": "🏆 Level 3",
        "level_4": "👑 Level 4",
        "level_5": "🚀 Level 5",

        # Corridors
        "corridor_info": "Corridor: ${min} - ${max} USDT",
        "enter_amount": "Enter deposit amount from ${min} to ${max} USDT:",
        "amount_below_min": "❌ Minimum amount: ${min} USDT",
        "amount_above_max": "❌ Maximum amount: ${max} USDT",

        # Statuses
        "status_active": "✅ Active",
        "status_locked": "🔒 Locked",
        "status_pending": "⏳ Pending Payment",

        # PLEX
        "plex_required": "PLEX required: {amount} tokens/day",
        "plex_payment_info": "💰 Daily payment: {amount} PLEX",
        "plex_deadline": "⏰ Payment deadline: {hours} hours",

        # Sequence
        "need_previous_level": "🔒 First unlock {level_name}",
        "level_already_active": "ℹ️ Level already active",
        "start_with_test": "👋 Start with test deposit",

        # Confirmations
        "confirm_deposit": """
📋 Deposit Confirmation

Level: {level_name}
Amount: ${amount} USDT
Daily PLEX: {plex_daily} tokens

Confirm?
        """,

        # Instructions
        "payment_instructions": """
💳 Payment Instructions

1️⃣ Send ${amount} USDT to address:
{wallet_address}

2️⃣ After USDT confirmation, send first PLEX payment:
{plex_amount} PLEX to the same address

⚠️ PLEX must be paid every 24 hours
        """,
    },

    "notifications": {
        "usdt_received": "✅ USDT payment received: ${amount}",
        "plex_received": "✅ PLEX payment received: {amount} tokens",
        "plex_reminder": "⏰ Reminder: PLEX payment required {amount} tokens",
        "plex_warning": "⚠️ WARNING: Deposit will be locked in {hours} hours!",
        "deposit_blocked": "❌ Deposit blocked for PLEX non-payment",
        "deposit_activated": "🎉 Deposit activated! Level: {level_name}",
    },
}


def get_deposit_translations(lang: str = "ru") -> dict:
    """
    Get deposit translations for specified language.

    Args:
        lang: Language code ('ru' or 'en')

    Returns:
        Dictionary with deposit and notification translations
    """
    translations = {
        "ru": RU_DEPOSIT_TRANSLATIONS,
        "en": EN_DEPOSIT_TRANSLATIONS,
    }
    return translations.get(lang, RU_DEPOSIT_TRANSLATIONS)
