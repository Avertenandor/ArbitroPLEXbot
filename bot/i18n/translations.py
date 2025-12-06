"""
Translation strings for all supported languages.

R13-3: Multi-language support for the bot.
"""

from bot.i18n.deposit_translations import (
    RU_DEPOSIT_TRANSLATIONS,
    EN_DEPOSIT_TRANSLATIONS,
)
from bot.i18n.auth_translations import (
    RU_AUTH_TRANSLATIONS,
    EN_AUTH_TRANSLATIONS,
)

# Russian translations (default)
RU_TRANSLATIONS = {
    "menu": {
        "main": "📊 *Главное меню*\n\nВыберите действие:",
        "deposit": "💰 Депозит",
        "withdrawal": "💸 Вывод",
        "balance": "📊 Баланс",
        "wallet_balance": "💰 Баланс кошелька",
        "referrals": "👥 Рефералы",
        "settings": "⚙️ Настройки",
        "support": "💬 Поддержка",
        "instructions": "📖 Инструкции",
        "history": "📜 История",
        "verification": "✅ Пройти верификацию",
        "finpass_recovery": "🔑 Восстановить финпароль",
        "appeal": "📝 Подать апелляцию",
    },
    "wallet_balance": {
        "title": "💰 *Баланс вашего кошелька*",
        "scanning": "⏳ *Сканирую баланс кошелька...*\n\nПодождите, идет проверка блокчейна...",
        "plex": "🟣 *PLEX:* `{balance}` PLEX",
        "usdt": "💵 *USDT:* `{balance}` USDT",
        "bnb": "🟡 *BNB:* `{balance}` BNB",
        "wallet_address": "📋 *Ваш кошелек (нажмите для копирования):*",
        "blockchain_note": "💡 _Баланс получен из блокчейна BSC_",
        "error": "⚠️ *Ошибка получения баланса*\n\nНе удалось получить баланс из блокчейна.\nПопробуйте позже.",
        "no_wallet": "❌ *Кошелек не найден*\n\nУ вас не указан адрес кошелька. Пожалуйста, пройдите регистрацию заново через /start",
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
        "user_not_found": "❌ Пользователь не найден",
        "balance_error": "❌ Ошибка получения баланса",
        "invalid_input": "❌ Неверный ввод. Попробуйте еще раз.",
        "operation_failed": "❌ Не удалось выполнить операцию",
        "user_load_error": (
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        ),
    },
    "auth": RU_AUTH_TRANSLATIONS["auth"],
    "deposit": RU_DEPOSIT_TRANSLATIONS["deposit"],
    "notifications": RU_DEPOSIT_TRANSLATIONS["notifications"],
    "payment": {
        "confirmed_scanning": (
            "✅ **Оплата подтверждена!**\n"
            "Транзакция: `{tx_hash_short}`\n\n"
            "⏳ Сканируем ваши депозиты..."
        ),
    },
    "withdrawal": {
        "menu_title": "💸 *Вывод средств*",
        "available_balance": "Доступно для вывода: `{amount} USDT`",
        "enter_amount": "Введите сумму для вывода (мин. {min_amount} USDT):",
        "enter_finpass": "🔐 Введите ваш финансовый пароль:",
        "cancelled": "❌ Вывод отменён.",
        "success": "✅ Заявка на вывод создана!",
        "insufficient_funds": "❌ Недостаточно средств",
        "min_amount_error": "❌ Минимальная сумма вывода: {min_amount} USDT",
        "finpass_required": (
            "❌ Для вывода необходим финансовый пароль!\n\n"
            "Установите финпароль через кнопку '🔐 Получить финпароль' в главном меню."
        ),
        "verification_required": (
            "❌ Для вывода с депозитами уровня 2+ требуется верификация!\n\n"
            "Укажите телефон или email через меню '👤 Мой профиль' → '✏️ Редактировать'."
        ),
        "confirmation_prompt": (
            "⚠️ *Подтверждение вывода*\n\n"
            "💰 Сумма: *{amount} USDT*\n"
            "💳 Кошелёк: `{wallet}`\n\n"
            "❗️ Убедитесь, что это ваш *ЛИЧНЫЙ* кошелёк (не биржевой)!\n\n"
            "Для подтверждения напишите: *да* или *yes*\n"
            "Для отмены: *нет* или *отмена*"
        ),
        "request_created": (
            "✅ *Заявка #{tx_id} создана!*\n\n"
            "💰 Запрошено: *{amount} USDT*\n"
            "💸 Комиссия: *{fee} USDT*\n"
            "✨ К получению: *{net_amount} USDT*\n"
            "💳 Кошелек: `{wallet}`\n\n"
            "⏱ *Время обработки:* до 24 часов\n"
            "📊 Статус можно проверить в '📜 История выводов'"
        ),
    },
    "verification": {
        "success": "✅ Верификация успешна!",
        "failed": "❌ Ошибка верификации",
        "user_not_found": "❌ Пользователь не найден. Попробуйте /start",
    },
    "support": {
        "menu_title": "💬 *Служба поддержки*",
        "choose_action": "Выберите действие из меню ниже:",
        "ticket_sent": "✅ Ваше обращение отправлено!",
        "ticket_error": "❌ Ошибка отправки обращения",
    },
    "profile": {
        "update_title": "📝 *Обновление контактов*",
        "phone_updated": "✅ Телефон успешно обновлен!",
        "email_updated": "✅ Email успешно обновлен!",
        "view_title": "👤 *Ваш профиль*",
        "basic_info": "*Основная информация:*",
        "user_id": "🆔 ID: `{user_id}`",
        "username": "👤 Username: @{username}",
        "wallet": "💳 Кошелек: `{wallet}`",
        "verification_status": "{emoji} Верификация: {status}",
        "verification_warning": (
            "⚠️ *Вывод недоступен* — нужен финпароль (кнопка '🔐 Получить финпароль')"
        ),
        "account_status": "{status}",
    },
}

# English translations
EN_TRANSLATIONS = {
    "menu": {
        "main": "📊 *Main Menu*\n\nChoose an action:",
        "deposit": "💰 Deposit",
        "withdrawal": "💸 Withdrawal",
        "balance": "📊 Balance",
        "wallet_balance": "💰 Wallet Balance",
        "referrals": "👥 Referrals",
        "settings": "⚙️ Settings",
        "support": "💬 Support",
        "instructions": "📖 Instructions",
        "history": "📜 History",
        "verification": "✅ Verify",
        "finpass_recovery": "🔑 Recover Financial Password",
        "appeal": "📝 Submit Appeal",
    },
    "wallet_balance": {
        "title": "💰 *Your Wallet Balance*",
        "scanning": "⏳ *Scanning wallet balance...*\n\nPlease wait, checking blockchain...",
        "plex": "🟣 *PLEX:* `{balance}` PLEX",
        "usdt": "💵 *USDT:* `{balance}` USDT",
        "bnb": "🟡 *BNB:* `{balance}` BNB",
        "wallet_address": "📋 *Your wallet (click to copy):*",
        "blockchain_note": "💡 _Balance retrieved from BSC blockchain_",
        "error": "⚠️ *Error getting balance*\n\nCould not retrieve balance from blockchain.\nPlease try again later.",
        "no_wallet": "❌ *Wallet not found*\n\nYou don't have a wallet address set. Please re-register via /start",
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
        "user_not_found": "❌ User not found",
        "balance_error": "❌ Error fetching balance",
        "invalid_input": "❌ Invalid input. Please try again.",
        "operation_failed": "❌ Operation failed",
        "user_load_error": (
            "⚠️ Error: could not load user data. "
            "Please try /start"
        ),
    },
    "auth": EN_AUTH_TRANSLATIONS["auth"],
    "deposit": EN_DEPOSIT_TRANSLATIONS["deposit"],
    "notifications": EN_DEPOSIT_TRANSLATIONS["notifications"],
    "payment": {
        "confirmed_scanning": (
            "✅ **Payment confirmed!**\n"
            "Transaction: `{tx_hash_short}`\n\n"
            "⏳ Scanning your deposits..."
        ),
    },
    "withdrawal": {
        "menu_title": "💸 *Withdrawal*",
        "available_balance": "Available for withdrawal: `{amount} USDT`",
        "enter_amount": "Enter withdrawal amount (min. {min_amount} USDT):",
        "enter_finpass": "🔐 Enter your financial password:",
        "cancelled": "❌ Withdrawal cancelled.",
        "success": "✅ Withdrawal request created!",
        "insufficient_funds": "❌ Insufficient funds",
        "min_amount_error": "❌ Minimum withdrawal amount: {min_amount} USDT",
        "finpass_required": (
            "❌ Financial password required for withdrawal!\n\n"
            "Set your financial password via '🔐 Get Financial Password' button in main menu."
        ),
        "verification_required": (
            "❌ Verification required for level 2+ deposits!\n\n"
            "Provide phone or email via '👤 My Profile' → '✏️ Edit'."
        ),
        "confirmation_prompt": (
            "⚠️ *Withdrawal Confirmation*\n\n"
            "💰 Amount: *{amount} USDT*\n"
            "💳 Wallet: `{wallet}`\n\n"
            "❗️ Make sure this is your *PERSONAL* wallet (not exchange)!\n\n"
            "To confirm, type: *yes*\n"
            "To cancel: *no* or *cancel*"
        ),
        "request_created": (
            "✅ *Request #{tx_id} created!*\n\n"
            "💰 Requested: *{amount} USDT*\n"
            "💸 Fee: *{fee} USDT*\n"
            "✨ To receive: *{net_amount} USDT*\n"
            "💳 Wallet: `{wallet}`\n\n"
            "⏱ *Processing time:* up to 24 hours\n"
            "📊 Check status in '📜 Withdrawal History'"
        ),
    },
    "verification": {
        "success": "✅ Verification successful!",
        "failed": "❌ Verification error",
        "user_not_found": "❌ User not found. Try /start",
    },
    "support": {
        "menu_title": "💬 *Support Service*",
        "choose_action": "Choose action from menu below:",
        "ticket_sent": "✅ Your request has been sent!",
        "ticket_error": "❌ Error sending request",
    },
    "profile": {
        "update_title": "📝 *Update Contacts*",
        "phone_updated": "✅ Phone successfully updated!",
        "email_updated": "✅ Email successfully updated!",
        "view_title": "👤 *Your Profile*",
        "basic_info": "*Basic Information:*",
        "user_id": "🆔 ID: `{user_id}`",
        "username": "👤 Username: @{username}",
        "wallet": "💳 Wallet: `{wallet}`",
        "verification_status": "{emoji} Verification: {status}",
        "verification_warning": (
            "⚠️ *Withdrawal unavailable* — financial password required "
            "(button '🔐 Get Financial Password')"
        ),
        "account_status": "{status}",
    },
}

# All translations
TRANSLATIONS = {
    "ru": RU_TRANSLATIONS,
    "en": EN_TRANSLATIONS,
}
