"""
Button text constants.

Centralized button text constants organized by category.
All button texts used in reply keyboards across the bot.
"""


# ============================================================================
# MAIN MENU BUTTONS (User)
# ============================================================================


class MainMenuButtons:
    """Main menu buttons for regular users."""

    # Balance & Transactions
    BALANCE = "📊 Баланс"
    WALLET_BALANCE = "💰 Баланс кошелька"
    DEPOSIT = "💰 Депозит"
    WITHDRAWAL = "💸 Вывод"
    MY_DEPOSITS = "📦 Мои депозиты"
    UPDATE_DEPOSIT = "🔄 Обновить депозит"
    TRANSACTION_HISTORY = "📜 История операций"

    # Referrals
    REFERRALS = "👥 Рефералы"

    # Support & Info
    SUPPORT = "💬 Поддержка"
    SETTINGS = "⚙️ Настройки"
    INSTRUCTIONS = "📖 Инструкции"
    CALCULATOR = "📊 Калькулятор"
    RULES = "📋 Правила"
    ECOSYSTEM_TOOLS = "🌐 Инструменты нашей экосистемы"

    # Financial Password
    GET_FINPASS = "🔐 Получить финпароль"
    RECOVER_FINPASS = "🔑 Восстановить финпароль"

    # Special
    BUY_RABBIT = "🐰 Купить кролика"
    REGISTRATION = "📝 Регистрация"


# ============================================================================
# ADMIN PANEL BUTTONS
# ============================================================================


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


# ============================================================================
# NAVIGATION BUTTONS
# ============================================================================


class NavigationButtons:
    """Navigation buttons used across the bot."""

    # Back buttons (different variants)
    BACK = "◀️ Назад"
    BACK_ARROW = "⬅ Назад"
    BACK_TO_WITHDRAWALS = "◀️ Назад к выводам"
    BACK_TO_ADMIN = "◀️ Назад в админ-панель"
    BACK_TO_LIST = "◀️ Назад к списку"
    BACK_TO_LEVELS = "◀️ Назад к уровням"
    BACK_TO_USERS = "◀️ К списку пользователей"
    BACK_TO_DEPOSIT_MGMT = "◀️ Назад в управление депозитами"
    BACK_TO_CARD = "◀️ К карточке"

    # Main menu buttons (different variants)
    MAIN_MENU = "📊 Главное меню"
    HOME = "🏠 Главное меню"
    TO_MAIN_MENU = "◀️ Главное меню"

    # Cancel buttons
    CANCEL = "❌ Отмена"
    CANCEL_ARROW = "◀️ Отмена"


# ============================================================================
# ACTION BUTTONS (Confirmation, Approval, etc.)
# ============================================================================


class ActionButtons:
    """Action buttons for confirmations and approvals."""

    # Confirmation
    YES = "✅ Да"
    NO = "❌ Нет"
    CONFIRM = "✅ Подтвердить"
    APPROVE = "✅ Одобрить"
    REJECT = "❌ Отклонить"

    # Submission
    SEND_REQUEST = "✅ Отправить заявку"
    CANCEL_ACTION = "❌ Отменить"

    # Special actions
    ADD_BUTTON = "✅ Добавить кнопку"
    SEND_WITHOUT_BUTTON = "🚀 Отправить без кнопки"
    I_PAID = "✅ Я оплатил"
    START_WORK = "🚀 Начать работу"
    APPLY = "✅ Да, применить"
    CANCEL_APPLY = "❌ Нет, отменить"
    APPROVE_REQUEST = "✅ Одобрить запрос"
    REJECT_REQUEST = "❌ Отклонить запрос"


# ============================================================================
# SUPPORT BUTTONS
# ============================================================================


class SupportButtons:
    """Support and ticket management buttons."""

    # User support
    CREATE_TICKET = "✉️ Создать обращение"
    MY_TICKETS = "📋 Мои обращения"
    FAQ = "❓ FAQ"

    # Admin support
    TICKET_LIST = "📋 Список обращений"
    FIND_TICKET = "🔍 Найти обращение"
    REPLY = "📝 Ответить"
    CLOSE = "🔒 Закрыть"
    REOPEN = "↩️ Переоткрыть"
    TAKE_TASK = "✋ Взять в работу"
    MY_TASKS = "🙋‍♂️ Мои задачи"


# ============================================================================
# DEPOSIT BUTTONS
# ============================================================================


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


# ============================================================================
# WITHDRAWAL BUTTONS
# ============================================================================


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


# ============================================================================
# REFERRAL BUTTONS
# ============================================================================


class ReferralButtons:
    """Referral system buttons."""

    MY_REFERRALS = "👥 Мои рефералы"
    MY_EARNINGS = "💰 Мой заработок"
    REFERRAL_STATS = "📊 Статистика рефералов"

    # Referral levels
    LEVEL_1 = "📊 Уровень 1"
    LEVEL_2 = "📊 Уровень 2"
    LEVEL_3 = "📊 Уровень 3"


# ============================================================================
# SETTINGS BUTTONS
# ============================================================================


class SettingsButtons:
    """Settings menu buttons."""

    MY_PROFILE = "👤 Мой профиль"
    MY_WALLET = "💳 Мой кошелек"
    NOTIFICATIONS = "🔔 Настройки уведомлений"
    UPDATE_CONTACTS = "📝 Обновить контакты"
    CHANGE_LANGUAGE = "🌐 Изменить язык"
    DOWNLOAD_REPORT = "📂 Скачать отчет"


# ============================================================================
# CONTACT UPDATE BUTTONS
# ============================================================================


class ContactButtons:
    """Contact update buttons."""

    UPDATE_PHONE = "📞 Обновить телефон"
    UPDATE_EMAIL = "📧 Обновить email"
    UPDATE_BOTH = "📝 Обновить оба"
    SKIP = "⏭ Пропустить"
    YES_LEAVE_CONTACTS = "✅ Да, оставить контакты"


# ============================================================================
# ADMIN USER MANAGEMENT BUTTONS
# ============================================================================


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


# ============================================================================
# ADMIN WALLET BUTTONS
# ============================================================================


class AdminWalletButtons:
    """Admin wallet management buttons."""

    WALLET_STATUS = "📊 Статус кошельков"
    SETUP_INCOMING = "📥 Настроить кошелек для входа"
    SETUP_OUTGOING = "📤 Настроить кошелек для выдачи"


# ============================================================================
# ADMIN BROADCAST BUTTONS
# ============================================================================


class BroadcastButtons:
    """Admin broadcast buttons."""

    ADD_BUTTON = "✅ Добавить кнопку"
    SEND_WITHOUT_BUTTON = "🚀 Отправить без кнопки"


# ============================================================================
# ADMIN BLACKLIST BUTTONS
# ============================================================================


class BlacklistButtons:
    """Admin blacklist management buttons."""

    ADD_TO_BLACKLIST = "➕ Добавить в blacklist"
    REMOVE_FROM_BLACKLIST = "🗑️ Удалить из blacklist"
    EDIT_TEXTS = "📝 Редактировать тексты"


# ============================================================================
# ADMIN MANAGEMENT BUTTONS
# ============================================================================


class AdminManagementButtons:
    """Admin management buttons (managing other admins)."""

    ADD_ADMIN = "➕ Добавить админа"
    ADMIN_LIST = "📋 Список админов"
    REMOVE_ADMIN = "🗑️ Удалить админа"
    EMERGENCY_BLOCK_ADMIN = "🛑 Экстренно заблокировать админа"


# ============================================================================
# ADMIN DEPOSIT MANAGEMENT BUTTONS
# ============================================================================


class AdminDepositButtons:
    """Admin deposit management buttons."""

    # Main menu
    DEPOSIT_STATS = "📊 Статистика по депозитам"
    FIND_USER_DEPOSITS = "🔍 Найти депозиты пользователя"
    MANAGE_LEVELS = "⚙️ Управление уровнями"
    PENDING_DEPOSITS = "📋 Pending депозиты"
    ROI_CORRIDORS = "💰 Коридоры доходности"
    ROI_STATISTICS = "📈 ROI статистика"
    CONFIGURE_LEVELS = "⚙️ Настроить уровни депозитов"

    # Level management
    LEVEL_1 = "Уровень 1"
    LEVEL_2 = "Уровень 2"
    LEVEL_3 = "Уровень 3"
    LEVEL_4 = "Уровень 4"
    LEVEL_5 = "Уровень 5"
    CHANGE_MAX_LEVEL = "🔢 Изм. макс. уровень"

    # Level actions
    CONFIGURE_ROI_CORRIDOR = "💰 Настроить коридор доходности"
    DISABLE_LEVEL = "❌ Отключить уровень"
    ENABLE_LEVEL = "✅ Включить уровень"


# ============================================================================
# NOTIFICATION SETTINGS BUTTONS
# ============================================================================


class NotificationButtons:
    """Notification settings toggle buttons."""

    # Deposit notifications
    DEPOSITS_ON = "✅ Уведомления о депозитах"
    DEPOSITS_OFF = "❌ Уведомления о депозитах"

    # Withdrawal notifications
    WITHDRAWALS_ON = "✅ Уведомления о выводах"
    WITHDRAWALS_OFF = "❌ Уведомления о выводах"

    # ROI notifications
    ROI_ON = "✅ Уведомления о ROI"
    ROI_OFF = "❌ Уведомления о ROI"

    # Marketing notifications
    MARKETING_ON = "✅ Маркетинговые уведомления"
    MARKETING_OFF = "❌ Маркетинговые уведомления"


# ============================================================================
# TRANSACTION HISTORY BUTTONS
# ============================================================================


class TransactionButtons:
    """Transaction history buttons."""

    # Type selection
    INTERNAL_TRANSACTIONS = "🔄 Внутренние транзакции"
    BLOCKCHAIN_TRANSACTIONS = "🔗 Транзакции в блокчейне"

    # Filters
    ALL_TRANSACTIONS = "📊 Все транзакции"
    DEPOSITS = "💰 Депозиты"
    WITHDRAWALS = "💸 Выводы"
    REFERRALS = "🎁 Реферальные"

    # Export
    DOWNLOAD_EXCEL = "📥 Скачать отчет (Excel)"


# ============================================================================
# PAGINATION BUTTONS
# ============================================================================


class PaginationButtons:
    """Pagination buttons (various formats)."""

    # Short format
    PREV_SHORT = "⬅️ Пред."
    NEXT_SHORT = "След. ➡️"

    # Medium format
    PREV_MEDIUM = "⬅️ Предыдущая"
    NEXT_MEDIUM = "Следующая ➡"

    # Long format
    PREV_PAGE = "⬅ Предыдущая страница"
    NEXT_PAGE = "➡ Следующая страница"

    # Specific contexts
    PREV_WITHDRAWAL_PAGE = "⬅ Предыдущая страница выводов"
    NEXT_WITHDRAWAL_PAGE = "➡ Следующая страница выводов"
    PREV_WITHDRAWAL_PAGE_ARROW = "⬅️ Предыдущая страница"
    NEXT_WITHDRAWAL_PAGE_ARROW = "➡️ Следующая страница"
    PREV_ADMIN_WITHDRAWAL = "⬅️ Пред. страница выводов"
    NEXT_ADMIN_WITHDRAWAL = "Вперёд страница выводов ➡️"


# ============================================================================
# MASTER KEY MANAGEMENT BUTTONS
# ============================================================================


class MasterKeyButtons:
    """Master key management buttons."""

    SHOW_CURRENT_KEY = "🔍 Показать текущий ключ"
    GENERATE_NEW_KEY = "🔄 Сгенерировать новый ключ"


# ============================================================================
# USER MESSAGES BUTTONS
# ============================================================================


class UserMessagesButtons:
    """User messages viewing buttons."""

    ANOTHER_USER = "🔍 Другой пользователь"
    DELETE_ALL_MESSAGES = "🗑 Удалить все сообщения"


# ============================================================================
# ROI CORRIDOR MANAGEMENT BUTTONS
# ============================================================================


class ROICorridorButtons:
    """ROI corridor management buttons."""

    # Main menu
    CONFIGURE_CORRIDORS = "⚙️ Настроить коридоры"
    CONFIGURE_LEVEL_AMOUNTS = "💵 Настроить суммы уровней"
    CURRENT_SETTINGS = "📊 Текущие настройки"
    CHANGE_HISTORY = "📜 История изменений"
    CONFIGURE_ACCRUAL_PERIOD = "⏱ Настроить период начисления"

    # Mode selection
    MODE_CUSTOM = "🎲 Custom (случайный из коридора)"
    MODE_EQUAL = "📊 Поровну (фиксированный для всех)"

    # Application scope
    APPLY_CURRENT_SESSION = "⚡️ Применить к текущей сессии"
    APPLY_NEXT_SESSION = "⏭ Применить к следующей сессии"


# ============================================================================
# FINANCIAL REPORT BUTTONS
# ============================================================================


class FinancialReportButtons:
    """Financial report buttons."""

    WITHDRAWAL_HISTORY = "💸 История выводов"
    ACCRUAL_HISTORY = "📜 История начислений"
    ALL_DEPOSITS = "📊 Все депозиты"
    ALL_WITHDRAWALS = "💸 Все выводы"
    WALLET_HISTORY = "💳 История кошельков"


# ============================================================================
# AUTHORIZATION (PAY-TO-USE) BUTTONS
# ============================================================================


class AuthButtons:
    """Authorization (pay-to-use) buttons."""

    I_PAID = "✅ Я оплатил"
    START_WORK = "🚀 Начать работу"
    UPDATE_DEPOSIT = "🔄 Обновить депозит"
    CONTINUE_WITHOUT_DEPOSIT = "🚀 Продолжить (без депозита)"
    CHECK_AGAIN = "🔄 Проверить снова"
    SHOW_PASSWORD_AGAIN = "🔑 Показать пароль ещё раз"


# ============================================================================
# WITHDRAWAL SETTINGS BUTTONS
# ============================================================================


class WithdrawalSettingsButtons:
    """Withdrawal settings buttons."""

    CHANGE_MIN_WITHDRAWAL = "💵 Изм. Мин. Вывод"
    CHANGE_DAILY_LIMIT = "🛡 Изм. Дневной Лимит"
    CHANGE_FEE = "💸 Изм. Комиссию (%)"
    DISABLE_LIMIT = "🔴 Выключить Лимит"
    ENABLE_LIMIT = "🟢 Включить Лимит"
    DISABLE_AUTO_WITHDRAWAL = "🔴 Выключить Авто-вывод"
    ENABLE_AUTO_WITHDRAWAL = "🟢 Включить Авто-вывод"


# ============================================================================
# APPEAL BUTTONS
# ============================================================================


class AppealButtons:
    """Appeal buttons for blocked users."""

    SUBMIT_APPEAL = "📝 Подать апелляцию"


# ============================================================================
# INLINE KEYBOARD BUTTON TEXTS
# ============================================================================


class InlineButtons:
    """Inline keyboard button texts (from inline.py)."""

    # Blockchain settings
    QUICKNODE = "QuickNode"
    QUICKNODE_ACTIVE = "✅ QuickNode"
    NODEREAL = "NodeReal"
    NODEREAL_ACTIVE = "✅ NodeReal"
    AUTO_SWITCH_ON = "✅ Авто-смена ВКЛ"
    AUTO_SWITCH_OFF = "❌ Авто-смена ВЫКЛ"
    REFRESH_STATUS = "🔄 Обновить статус"

    # Finpass recovery
    APPROVE = "✅ Одобрить"
    REJECT = "❌ Отклонить"
