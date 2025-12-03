"""
Translation strings for all supported languages.

R13-3: Multi-language support for the bot.
"""

# Russian translations (default)
RU_TRANSLATIONS = {
    "menu": {
        "main": "📊 *Главное меню*\n\nВыберите действие:",
        "deposit": "💰 Депозит",
        "withdrawal": "💸 Вывод",
        "balance": "📊 Баланс",
        "referrals": "👥 Рефералы",
        "settings": "⚙️ Настройки",
        "support": "💬 Поддержка",
        "instructions": "📖 Инструкции",
        "history": "📜 История",
        "verification": "✅ Пройти верификацию",
        "finpass_recovery": "🔑 Восстановить финпароль",
        "appeal": "📝 Подать апелляцию",
    },
    "settings": {
        "title": "⚙️ *Настройки*\n\nВыберите действие:",
        "profile": "👤 Мой профиль",
        "wallet": "💳 Мой кошелек",
        "notifications": "🔔 Настройки уведомлений",
        "contacts": "📝 Обновить контакты",
        "language": "🌐 Изменить язык",
    },
    "language": {
        "title": "🌐 *Выбор языка*\n\nВыберите язык:",
        "changed": "✅ Язык изменён на {language}",
        "error": "❌ Ошибка при изменении языка",
    },
    "common": {
        "back": "◀️ Назад",
        "cancel": "❌ Отмена",
        "confirm": "✅ Подтвердить",
        "error": "⚠️ Произошла ошибка. Попробуйте позже.",
        "not_registered": "❌ Пожалуйста, сначала зарегистрируйтесь",
        "welcome_back": "Добро пожаловать обратно, {username}!",
        "your_balance": "Ваш баланс: {balance} USDT",
        "use_menu": "Используйте меню ниже для навигации.",
        "choose_action": "Выберите действие ниже:",
        "welcome": "👋 Добро пожаловать обратно!",
        "user": "пользователь",
        "welcome_user": "Добро пожаловать, {username}!",
    },
    "errors": {
        "database_unavailable": (
            "⚠️ Технические работы, сервис временно недоступен.\n\n"
            "Ваши средства в безопасности, все операции будут "
            "обработаны после восстановления.\n\n"
            "Попробуйте через 5-10 минут."
        ),
        "database_connection_failed": (
            "⚠️ Проблема с подключением к базе данных.\n\n"
            "Ваши средства в безопасности. "
            "Попробуйте позже или обратитесь в поддержку."
        ),
        "database_operational_error": (
            "⚠️ Временная недоступность базы данных.\n\n"
            "Ваши средства в безопасности. "
            "Все операции будут обработаны после восстановления.\n\n"
            "Попробуйте через несколько минут."
        ),
        "database_interface_error": (
            "⚠️ Проблема с подключением к базе данных.\n\n"
            "Ваши средства в безопасности. "
            "Попробуйте позже или обратитесь в поддержку."
        ),
        "database_general_error": (
            "⚠️ Ошибка базы данных.\n\n"
            "Ваши средства в безопасности. "
            "Попробуйте позже или обратитесь в поддержку."
        ),
        "system_error": (
            "⚠️ Системная ошибка.\n\n"
            "Попробуйте позже или обратитесь в поддержку."
        ),
    },
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
    "deposit": {
        "scanning": "⏳ Сканируем депозиты...",
        "scanning_your_deposits": "⏳ Сканируем ваши депозиты...",
        "confirmed": "✅ **Депозит подтверждён!**",
        "user_not_found": "⚠️ Пользователь не найден. Введите /start",
    },
    "payment": {
        "confirmed_scanning": (
            "✅ **Оплата подтверждена!**\n"
            "Транзакция: `{tx_hash_short}`\n\n"
            "⏳ Сканируем ваши депозиты..."
        ),
    },
}

# English translations
EN_TRANSLATIONS = {
    "menu": {
        "main": "📊 *Main Menu*\n\nChoose an action:",
        "deposit": "💰 Deposit",
        "withdrawal": "💸 Withdrawal",
        "balance": "📊 Balance",
        "referrals": "👥 Referrals",
        "settings": "⚙️ Settings",
        "support": "💬 Support",
        "instructions": "📖 Instructions",
        "history": "📜 History",
        "verification": "✅ Verify",
        "finpass_recovery": "🔑 Recover Financial Password",
        "appeal": "📝 Submit Appeal",
    },
    "settings": {
        "title": "⚙️ *Settings*\n\nChoose an action:",
        "profile": "👤 My Profile",
        "wallet": "💳 My Wallet",
        "notifications": "🔔 Notification Settings",
        "contacts": "📝 Update Contacts",
        "language": "🌐 Change Language",
    },
    "language": {
        "title": "🌐 *Language Selection*\n\nChoose a language:",
        "changed": "✅ Language changed to {language}",
        "error": "❌ Error changing language",
    },
    "common": {
        "back": "◀️ Back",
        "cancel": "❌ Cancel",
        "confirm": "✅ Confirm",
        "error": "⚠️ An error occurred. Please try again later.",
        "not_registered": "❌ Please register first",
        "welcome_back": "Welcome back, {username}!",
        "your_balance": "Your balance: {balance} USDT",
        "use_menu": "Use the menu below to navigate.",
        "choose_action": "Choose an action below:",
        "welcome": "👋 Welcome back!",
        "user": "user",
        "welcome_user": "Welcome, {username}!",
    },
    "errors": {
        "database_unavailable": (
            "⚠️ Technical maintenance, service temporarily unavailable.\n\n"
            "Your funds are safe, all operations will be "
            "processed after restoration.\n\n"
            "Please try again in 5-10 minutes."
        ),
        "database_connection_failed": (
            "⚠️ Database connection problem.\n\n"
            "Your funds are safe. "
            "Please try again later or contact support."
        ),
        "database_operational_error": (
            "⚠️ Database temporarily unavailable.\n\n"
            "Your funds are safe. "
            "All operations will be processed after restoration.\n\n"
            "Please try again in a few minutes."
        ),
        "database_interface_error": (
            "⚠️ Database connection problem.\n\n"
            "Your funds are safe. "
            "Please try again later or contact support."
        ),
        "database_general_error": (
            "⚠️ Database error.\n\n"
            "Your funds are safe. "
            "Please try again later or contact support."
        ),
        "system_error": (
            "⚠️ System error.\n\n"
            "Please try again later or contact support."
        ),
    },
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
    "deposit": {
        "scanning": "⏳ Scanning deposits...",
        "scanning_your_deposits": "⏳ Scanning your deposits...",
        "confirmed": "✅ **Deposit confirmed!**",
        "user_not_found": "⚠️ User not found. Send /start",
    },
    "payment": {
        "confirmed_scanning": (
            "✅ **Payment confirmed!**\n"
            "Transaction: `{tx_hash_short}`\n\n"
            "⏳ Scanning your deposits..."
        ),
    },
}

# All translations
TRANSLATIONS = {
    "ru": RU_TRANSLATIONS,
    "en": EN_TRANSLATIONS,
}

