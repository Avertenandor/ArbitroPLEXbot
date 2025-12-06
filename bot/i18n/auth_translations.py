"""
Authentication-specific translations for the bot.

This module contains all auth-related translations.
"""

# Russian auth translations
RU_AUTH_TRANSLATIONS = {
    "auth": {
        "welcome_unregistered": (
            "🚀 **Добро пожаловать в ArbitroPLEXbot!**\n\n"
            "Мы строим **крипто-фиатную экосистему** на базе монеты "
            "**PLEX** и высокодоходных торговых роботов.\n\n"
            "🔐 **Доступ к нашей системе** осуществляется через этого бота.\n\n"
            "📊 **Доход:** от **30% до 70%** в день!\n\n"
            "📋 **УРОВНИ ДОСТУПА:**\n"
            "{levels_table}\n\n"
            "{rules_short}\n\n"
            "🔑 **АВТОРИЗАЦИЯ**\n\n"
            "Для входа в систему необходимо:\n"
            "1️⃣ Указать адрес вашего кошелька\n"
            "2️⃣ Оплатить 10 PLEX за доступ\n\n"
            "💼 **Введите адрес вашего BSC кошелька:**\n"
            "_(Формат: 0x...)_"
        ),
        "wallet_accepted": (
            "✅ **Кошелёк принят!**\n"
            "`{wallet_short}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💰 **Оплата доступа**\n\n"
            "Отправьте **{price} PLEX** на кошелёк:\n"
            "`{system_wallet}`\n"
            "_(Нажмите для копирования)_\n\n"
            "📌 **Контракт PLEX:**\n"
            "`{token_addr}`\n\n"
            "📱 **QR-код ниже** — отсканируйте в кошельке для быстрой отправки.\n\n"
            "После оплаты нажмите кнопку ниже."
        ),
        "qr_caption": "📱 QR-код кошелька для оплаты\n`{system_wallet}`",
        "auth_cancelled": (
            "Авторизация отменена.\n\n"
            "Чтобы войти позже, используйте команду /start."
        ),
        "invalid_address": (
            "❌ **Неверный формат адреса!**\n\n"
            "Адрес должен начинаться с `0x` и содержать 42 символа.\n\n"
            "📎 Введите корректный адрес:"
        ),
        "insufficient_plex": (
            "⚠️ На вашем кошельке недостаточно PLEX для минимального уровня доступа.\n\n"
            "Текущий баланс PLEX: `{plex_balance}`\n"
            "Требуемый минимум: `{minimum_plex}` PLEX.\n\n"
            "Вы всё равно можете продолжить авторизацию, но доступ к части "
            "функций может быть ограничен."
        ),
        "enter_payment_wallet": (
            "📎 Введите адрес кошелька, с которого был совершен перевод:\n"
            "Формат: `0x...`"
        ),
    },
}

# English auth translations
EN_AUTH_TRANSLATIONS = {
    "auth": {
        "welcome_unregistered": (
            "🚀 **Welcome to ArbitroPLEXbot!**\n\n"
            "We build **crypto-fiat ecosystem** based on "
            "**PLEX** token and high-profit trading bots.\n\n"
            "🔐 **Access to our system** is through this bot.\n\n"
            "📊 **Profit:** from **30% to 70%** per day!\n\n"
            "📋 **ACCESS LEVELS:**\n"
            "{levels_table}\n\n"
            "{rules_short}\n\n"
            "🔑 **AUTHORIZATION**\n\n"
            "To access the system you need to:\n"
            "1️⃣ Provide your wallet address\n"
            "2️⃣ Pay 10 PLEX for access\n\n"
            "💼 **Enter your BSC wallet address:**\n"
            "_(Format: 0x...)_"
        ),
        "wallet_accepted": (
            "✅ **Wallet accepted!**\n"
            "`{wallet_short}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💰 **Access payment**\n\n"
            "Send **{price} PLEX** to wallet:\n"
            "`{system_wallet}`\n"
            "_(Click to copy)_\n\n"
            "📌 **PLEX Contract:**\n"
            "`{token_addr}`\n\n"
            "📱 **QR code below** — scan in your wallet for quick transfer.\n\n"
            "After payment, press the button below."
        ),
        "qr_caption": "📱 Wallet QR code for payment\n`{system_wallet}`",
        "auth_cancelled": (
            "Authorization cancelled.\n\n"
            "To log in later, use /start command."
        ),
        "invalid_address": (
            "❌ **Invalid address format!**\n\n"
            "Address must start with `0x` and contain 42 characters.\n\n"
            "📎 Enter correct address:"
        ),
        "insufficient_plex": (
            "⚠️ Your wallet has insufficient PLEX for minimum access level.\n\n"
            "Current PLEX balance: `{plex_balance}`\n"
            "Required minimum: `{minimum_plex}` PLEX.\n\n"
            "You can still proceed with authorization, but access to some "
            "features may be limited."
        ),
        "enter_payment_wallet": (
            "📎 Enter the wallet address from which the transfer was made:\n"
            "Format: `0x...`"
        ),
    },
}
