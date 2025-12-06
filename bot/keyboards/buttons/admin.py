"""Admin panel button constants."""


class AdminButtons:
    """Admin panel main buttons."""

    ADMIN_PANEL = "👑 Админ-панель"
    STATISTICS = "📊 Статистика"
    USER_MANAGEMENT = "👥 Управление пользователями"
    WITHDRAWAL_REQUESTS = "💸 Заявки на вывод"
    WITHDRAWAL_HISTORY = "📋 История выводов"
    BROADCAST = "📢 Рассылка"
    SUPPORT = "🆘 Техподдержка"
    FINANCIAL_REPORT = "💰 Финансовая отчётность"
    FINPASS_RECOVERY = "🔑 Восстановление пароля"
    VIEW_USER_MESSAGES = "📝 Просмотр сообщений пользователей"
    WALLET_MANAGEMENT = "🔐 Управление кошельком"
    BLOCKCHAIN_SETTINGS = "📡 Блокчейн Настройки"
    BLACKLIST_MANAGEMENT = "🚫 Управление черным списком"
    DEPOSIT_MANAGEMENT = "💰 Управление депозитами"
    EMERGENCY_STOPS = "🚨 Аварийные стопы"
    ADMIN_MANAGEMENT = "👥 Управление админами"
    MASTER_KEY_MANAGEMENT = "🔑 Управление мастер-ключом"


class AdminUserButtons:
    """Admin user management buttons."""

    FIND_USER = "🔍 Найти пользователя"
    USER_LIST = "👥 Список пользователей"
    BLOCK_USER = "🚫 Заблокировать пользователя"
    TERMINATE_ACCOUNT = "⚠️ Терминировать аккаунт"

    # User profile actions
    CHANGE_BALANCE = "💳 Изменить баланс"
    UNBLOCK = "✅ Разблокировать"
    BLOCK = "🚫 Заблокировать"
    TRANSACTION_HISTORY = "📜 История транзакций"
    REFERRALS = "👥 Рефералы"
    SCAN_DEPOSIT = "🔄 Сканировать депозит"


class AdminWalletButtons:
    """Admin wallet management buttons."""

    WALLET_STATUS = "📊 Статус кошельков"
    SETUP_INCOMING = "📥 Настроить кошелек для входа"
    SETUP_OUTGOING = "📤 Настроить кошелек для выдачи"


class AdminManagementButtons:
    """Admin management buttons (managing other admins)."""

    ADD_ADMIN = "➕ Добавить админа"
    ADMIN_LIST = "📋 Список админов"
    REMOVE_ADMIN = "🗑️ Удалить админа"
    EMERGENCY_BLOCK_ADMIN = "🛑 Экстренно заблокировать админа"
