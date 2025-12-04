"""
Admin keyboards module.

Reply keyboards for admin panel and management operations.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_admin_keyboard_from_data(data: dict) -> ReplyKeyboardMarkup:
    """
    Get admin keyboard using role flags from handler data.

    Args:
        data: Handler data dict. Expected keys:
            - is_super_admin: bool
            - is_extended_admin: bool

    Returns:
        ReplyKeyboardMarkup with admin options filtered by role.
    """
    is_super_admin = data.get("is_super_admin", False)
    is_extended_admin = data.get("is_extended_admin", False)
    return admin_keyboard(
        is_super_admin=is_super_admin,
        is_extended_admin=is_extended_admin,
    )


def admin_keyboard(
    is_super_admin: bool = False,
    is_extended_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Admin panel reply keyboard.

    Args:
        is_super_admin: Whether current admin is super admin
        is_extended_admin: Whether current admin is extended admin

    Returns:
        ReplyKeyboardMarkup with admin options, filtered by role.
    """
    builder = ReplyKeyboardBuilder()

    # Common buttons for ALL admins (Basic, Extended, Super)
    builder.row(KeyboardButton(text="📊 Статистика"))
    builder.row(KeyboardButton(text="👥 Управление пользователями"))
    builder.row(
        KeyboardButton(text="💸 Заявки на вывод"),
        KeyboardButton(text="📋 История выводов"),
    )
    builder.row(
        KeyboardButton(text="📢 Рассылка"),
        KeyboardButton(text="🆘 Техподдержка"),
    )

    # Financial Reports & Finpass Recovery (Safe for all admins per request)
    builder.row(
        KeyboardButton(text="💰 Финансовая отчётность"),
        KeyboardButton(text="🔑 Восстановление пароля"),
    )

    # User inquiries (questions from users)
    builder.row(KeyboardButton(text="📨 Обращения от пользователей"))

    builder.row(KeyboardButton(text="📝 Просмотр сообщений пользователей"))

    # Sensitive controls - Extended/Super only
    if is_extended_admin or is_super_admin:
        builder.row(
            KeyboardButton(text="🔐 Управление кошельком"),
            KeyboardButton(text="📡 Блокчейн Настройки"),
        )
        builder.row(
            KeyboardButton(text="🚫 Управление черным списком"),
        )
        builder.row(KeyboardButton(text="💰 Управление депозитами"))
        builder.row(KeyboardButton(text="🚨 Аварийные стопы"))

    # Super Admin only
    if is_super_admin:
        builder.row(KeyboardButton(text="👥 Управление админами"))
        builder.row(KeyboardButton(text="🔑 Управление мастер-ключом"))

    builder.row(KeyboardButton(text="◀️ Главное меню"))

    return builder.as_markup(resize_keyboard=True)


def admin_users_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin users management keyboard.

    Returns:
        ReplyKeyboardMarkup with user management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🔍 Найти пользователя"),
    )
    builder.row(
        KeyboardButton(text="👥 Список пользователей"),
    )
    builder.row(
        KeyboardButton(text="🚫 Заблокировать пользователя"),
    )
    builder.row(
        KeyboardButton(text="⚠️ Терминировать аккаунт"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_withdrawals_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin withdrawals management keyboard.

    Returns:
        ReplyKeyboardMarkup with withdrawal management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="⏳ Ожидающие выводы"),
    )
    builder.row(
        KeyboardButton(text="📋 Одобренные выводы"),
        KeyboardButton(text="🚫 Отклоненные выводы"),
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки выплат"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def withdrawal_list_keyboard(
    withdrawals: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with withdrawal buttons for admin selection.

    Args:
        withdrawals: List of Transaction objects (pending withdrawals)
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with withdrawal buttons
    """
    from bot.utils.formatters import format_usdt

    builder = ReplyKeyboardBuilder()

    # Withdrawal buttons (1 per row for clarity)
    for wd in withdrawals:
        amount_str = format_usdt(wd.amount)
        user_label = f"ID:{wd.user_id}"
        if hasattr(wd, "user") and wd.user and wd.user.username:
            user_label = f"@{wd.user.username}"
        # Neutral emoji for selection
        builder.row(
            KeyboardButton(text=f"💸 #{wd.id} | {amount_str} | {user_label}")
        )

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅️ Пред."))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="След. ➡️"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(KeyboardButton(text="◀️ Назад к выводам"))

    return builder.as_markup(resize_keyboard=True)


def admin_withdrawal_detail_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for viewing a specific withdrawal request details.

    Returns:
        ReplyKeyboardMarkup with action buttons
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Одобрить"),
        KeyboardButton(text="❌ Отклонить")
    )
    builder.row(
        KeyboardButton(text="◀️ Назад к списку"),
        KeyboardButton(text="👑 Админ-панель")
    )
    return builder.as_markup(resize_keyboard=True)


def withdrawal_confirm_keyboard(withdrawal_id: int, action: str) -> ReplyKeyboardMarkup:
    """Keyboard for confirming withdrawal action."""
    builder = ReplyKeyboardBuilder()
    action_text = "Одобрить" if action == "approve" else "Отклонить"
    builder.row(
        KeyboardButton(text=f"✅ Да, {action_text.lower()} #{withdrawal_id}"),
    )
    builder.row(
        KeyboardButton(text="❌ Нет, отменить"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_wallet_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin wallet management keyboard.

    Returns:
        ReplyKeyboardMarkup with wallet management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📊 Статус кошельков"),
    )
    builder.row(
        KeyboardButton(text="📥 Настроить кошелек для входа"),
    )
    builder.row(
        KeyboardButton(text="📤 Настроить кошелек для выдачи"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_broadcast_button_choice_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin broadcast button choice keyboard.

    Returns:
        ReplyKeyboardMarkup with button options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="✅ Добавить кнопку"),
        KeyboardButton(text="🚀 Отправить без кнопки"),
    )
    builder.row(
        KeyboardButton(text="❌ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_broadcast_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin broadcast cancel keyboard.

    Returns:
        ReplyKeyboardMarkup with cancel option
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_broadcast_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin broadcast keyboard.

    Returns:
        ReplyKeyboardMarkup with broadcast options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Отмена"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_support_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin support keyboard.

    Returns:
        ReplyKeyboardMarkup with support options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📋 Список обращений"),
        KeyboardButton(text="🔍 Найти обращение"),
    )
    builder.row(
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="🙋‍♂️ Мои задачи"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_support_ticket_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for viewing a specific ticket.

    Returns:
        ReplyKeyboardMarkup with ticket actions
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📝 Ответить"))
    builder.row(KeyboardButton(text="🔒 Закрыть"), KeyboardButton(text="↩️ Переоткрыть"))
    builder.row(KeyboardButton(text="✋ Взять в работу"))
    builder.row(KeyboardButton(text="◀️ Назад к списку"), KeyboardButton(text="👑 Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def admin_blacklist_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin blacklist management keyboard.

    Returns:
        ReplyKeyboardMarkup with blacklist management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="➕ Добавить в blacklist"),
    )
    builder.row(
        KeyboardButton(text="🗑️ Удалить из blacklist"),
    )
    builder.row(
        KeyboardButton(text="📝 Редактировать тексты"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_management_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin management keyboard (for managing admins).

    Returns:
        ReplyKeyboardMarkup with admin management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="➕ Добавить админа"),
    )
    builder.row(
        KeyboardButton(text="📋 Список админов"),
    )
    builder.row(
        KeyboardButton(text="🗑️ Удалить админа"),
    )
    builder.row(
        KeyboardButton(text="🛑 Экстренно заблокировать админа"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_deposit_settings_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin deposit settings keyboard.

    Returns:
        ReplyKeyboardMarkup with deposit settings options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="⚙️ Настроить уровни депозитов"),
    )
    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_deposit_management_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin deposit management main menu keyboard.

    Returns:
        ReplyKeyboardMarkup with deposit management options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📊 Статистика по депозитам"),
    )
    builder.row(
        KeyboardButton(text="🔍 Найти депозиты пользователя"),
    )
    builder.row(
        KeyboardButton(text="⚙️ Управление уровнями"),
    )
    builder.row(
        KeyboardButton(text="📋 Pending депозиты"),
    )
    builder.row(
        KeyboardButton(text="💰 Коридоры доходности"),
    )
    builder.row(
        KeyboardButton(text="📈 ROI статистика"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад в админ-панель"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_deposit_levels_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin deposit levels selection keyboard.

    Returns:
        ReplyKeyboardMarkup with level selection buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="Уровень 1"),
        KeyboardButton(text="Уровень 2"),
    )
    builder.row(
        KeyboardButton(text="Уровень 3"),
        KeyboardButton(text="Уровень 4"),
    )
    builder.row(
        KeyboardButton(text="Уровень 5"),
    )
    builder.row(
        KeyboardButton(text="🔢 Изм. макс. уровень"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад в админ-панель"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_deposit_level_actions_keyboard(
    level: int, is_active: bool
) -> ReplyKeyboardMarkup:
    """
    Admin deposit level actions keyboard.

    Args:
        level: Deposit level number (1-5)
        is_active: Whether level is currently active

    Returns:
        ReplyKeyboardMarkup with level action buttons
    """
    builder = ReplyKeyboardBuilder()

    # ROI Corridor management button (main feature)
    builder.row(
        KeyboardButton(text="💰 Настроить коридор доходности"),
    )

    # Enable/Disable level button
    if is_active:
        builder.row(
            KeyboardButton(text="❌ Отключить уровень"),
        )
    else:
        builder.row(
            KeyboardButton(text="✅ Включить уровень"),
        )

    # Back button
    builder.row(
        KeyboardButton(text="◀️ Назад к уровням"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_roi_corridor_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    ROI corridor management menu keyboard.

    Returns:
        ReplyKeyboardMarkup with ROI corridor menu options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⚙️ Настроить коридоры"))
    builder.row(KeyboardButton(text="💵 Настроить суммы уровней"))
    builder.row(KeyboardButton(text="📊 Текущие настройки"))
    builder.row(KeyboardButton(text="📜 История изменений"))
    builder.row(KeyboardButton(text="⏱ Настроить период начисления"))
    builder.row(KeyboardButton(text="◀️ Назад в управление депозитами"))
    builder.row(KeyboardButton(text="👑 Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def admin_roi_level_select_keyboard() -> ReplyKeyboardMarkup:
    """
    Level selection keyboard for ROI corridor management.

    Returns:
        ReplyKeyboardMarkup with level selection buttons
    """
    builder = ReplyKeyboardBuilder()
    for i in range(1, 6):
        builder.row(KeyboardButton(text=f"Уровень {i}"))
    builder.row(
        KeyboardButton(text="◀️ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_roi_mode_select_keyboard() -> ReplyKeyboardMarkup:
    """
    Mode selection keyboard for ROI corridor.

    Returns:
        ReplyKeyboardMarkup with mode selection buttons
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🎲 Custom (случайный из коридора)"))
    builder.row(KeyboardButton(text="📊 Поровну (фиксированный для всех)"))
    builder.row(
        KeyboardButton(text="◀️ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_roi_applies_to_keyboard() -> ReplyKeyboardMarkup:
    """
    Application scope selection keyboard.

    Returns:
        ReplyKeyboardMarkup with application scope buttons
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⚡️ Применить к текущей сессии"))
    builder.row(KeyboardButton(text="⏭ Применить к следующей сессии"))
    builder.row(
        KeyboardButton(text="◀️ Отмена"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_roi_confirmation_keyboard() -> ReplyKeyboardMarkup:
    """
    Confirmation keyboard for ROI corridor settings.

    Returns:
        ReplyKeyboardMarkup with confirmation buttons
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="✅ Да, применить"))
    builder.row(KeyboardButton(text="❌ Нет, отменить"))
    return builder.as_markup(resize_keyboard=True)


def admin_ticket_list_keyboard(
    tickets: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with ticket buttons for admin selection.

    Args:
        tickets: List of SupportTicket objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with ticket buttons
    """
    builder = ReplyKeyboardBuilder()

    # Ticket buttons (2 per row)
    for i in range(0, len(tickets), 2):
        row_buttons = []
        # Button 1
        t1 = tickets[i]
        user_label1 = f"ID: {t1.user_id}"
        if t1.user and t1.user.username:
            user_label1 = f"@{t1.user.username}"
        row_buttons.append(KeyboardButton(text=f"🎫 #{t1.id} {user_label1}"))

        # Button 2 (if exists)
        if i + 1 < len(tickets):
            t2 = tickets[i + 1]
            user_label2 = f"ID: {t2.user_id}"
            if t2.user and t2.user.username:
                user_label2 = f"@{t2.user.username}"
            row_buttons.append(KeyboardButton(text=f"🎫 #{t2.id} {user_label2}"))

        builder.row(*row_buttons)

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="Следующая ➡"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="🆘 Техподдержка"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_user_list_keyboard(
    users: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with user buttons for admin selection.

    Args:
        users: List of User objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with user buttons
    """
    builder = ReplyKeyboardBuilder()

    # User buttons (2 per row)
    for i in range(0, len(users), 2):
        row_buttons = []
        u1 = users[i]
        label1 = f"@{u1.username}" if u1.username else f"ID {u1.telegram_id}"
        # Button text format: "🆔 {id}: {label}" to easily parse ID later
        row_buttons.append(KeyboardButton(text=f"🆔 {u1.id}: {label1}"))

        if i + 1 < len(users):
            u2 = users[i + 1]
            label2 = f"@{u2.username}" if u2.username else f"ID {u2.telegram_id}"
            row_buttons.append(KeyboardButton(text=f"🆔 {u2.id}: {label2}"))

        builder.row(*row_buttons)

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="Следующая ➡"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="👥 Управление пользователями"),
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_user_profile_keyboard(user_is_blocked: bool) -> ReplyKeyboardMarkup:
    """
    Keyboard for managing a specific user.

    Args:
        user_is_blocked: Whether the user is currently blocked

    Returns:
        ReplyKeyboardMarkup with user profile actions
    """
    builder = ReplyKeyboardBuilder()

    block_text = "✅ Разблокировать" if user_is_blocked else "🚫 Заблокировать"

    builder.row(
        KeyboardButton(text="💳 Изменить баланс"),
        KeyboardButton(text=block_text),
    )
    builder.row(
        KeyboardButton(text="📜 История транзакций"),
        KeyboardButton(text="👥 Рефералы"),
    )
    builder.row(
        KeyboardButton(text="🔄 Сканировать депозит"),
        KeyboardButton(text="⚠️ Терминировать аккаунт"),
    )
    builder.row(
        KeyboardButton(text="◀️ К списку пользователей"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_finpass_request_list_keyboard(
    requests: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with finpass recovery request buttons for admin selection.

    Args:
        requests: List of FinpassRecoveryRequest objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with request buttons
    """
    builder = ReplyKeyboardBuilder()

    # Request buttons (2 per row)
    for i in range(0, len(requests), 2):
        row_buttons = []
        # Button 1
        r1 = requests[i]
        # Try to get user label if available (joined) or just ID
        user_label1 = f"User {r1.user_id}"
        if hasattr(r1, 'user') and r1.user:
             if r1.user.username:
                 user_label1 = f"@{r1.user.username}"
             elif r1.user.telegram_id:
                 user_label1 = f"TG {r1.user.telegram_id}"

        row_buttons.append(KeyboardButton(text=f"🔑 Запрос #{r1.id} {user_label1}"))

        # Button 2 (if exists)
        if i + 1 < len(requests):
            r2 = requests[i + 1]
            user_label2 = f"User {r2.user_id}"
            if hasattr(r2, 'user') and r2.user:
                 if r2.user.username:
                     user_label2 = f"@{r2.user.username}"
                 elif r2.user.telegram_id:
                     user_label2 = f"TG {r2.user.telegram_id}"
            row_buttons.append(KeyboardButton(text=f"🔑 Запрос #{r2.id} {user_label2}"))

        builder.row(*row_buttons)

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="Следующая ➡"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="👑 Админ-панель"),
    )

    return builder.as_markup(resize_keyboard=True)


def admin_finpass_request_actions_keyboard() -> ReplyKeyboardMarkup:
    """
    Actions keyboard for a specific finpass recovery request.

    Returns:
        ReplyKeyboardMarkup with actions
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Одобрить запрос"),
        KeyboardButton(text="❌ Отклонить запрос"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад к списку"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_financial_list_keyboard(
    users: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with users for financial report selection.

    Args:
        users: List of UserFinancialDTO objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()

    for user in users:
        # Truncate if too long, but try to show financial summary
        username = user.username or str(user.telegram_id)
        if len(username) > 15:
            username = username[:12] + "..."

        text = f"👤 {user.id}. {username} | +{int(user.total_deposited)} | -{int(user.total_withdrawn)}"
        builder.row(KeyboardButton(text=text))

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="Следующая ➡"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(KeyboardButton(text="👑 Админ-панель"))

    return builder.as_markup(resize_keyboard=True)


def admin_user_financial_keyboard() -> ReplyKeyboardMarkup:
    """
    Actions for a selected user in financial report.

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="💸 История выводов"),
        KeyboardButton(text="📜 История начислений"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад к списку"),
        KeyboardButton(text="👑 Админ-панель"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_back_keyboard() -> ReplyKeyboardMarkup:
    """
    Simple back keyboard.

    Returns:
        ReplyKeyboardMarkup
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="◀️ Назад"))
    builder.row(KeyboardButton(text="👑 Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def admin_user_financial_detail_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for detailed user financial card.

    Returns:
        ReplyKeyboardMarkup with navigation options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📊 Все депозиты"))
    builder.row(KeyboardButton(text="💸 Все выводы"))
    builder.row(KeyboardButton(text="💳 История кошельков"))
    builder.row(
        KeyboardButton(text="⬅ Назад к списку"),
        KeyboardButton(text="👑 Админ-панель")
    )
    return builder.as_markup(resize_keyboard=True)


def admin_deposits_list_keyboard(
    page: int = 1, total_pages: int = 1
) -> ReplyKeyboardMarkup:
    """
    Keyboard for deposits list with pagination.

    Args:
        page: Current page number
        total_pages: Total number of pages

    Returns:
        ReplyKeyboardMarkup with pagination
    """
    builder = ReplyKeyboardBuilder()

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="Следующая ➡"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="◀️ К карточке"),
        KeyboardButton(text="👑 Админ-панель")
    )

    return builder.as_markup(resize_keyboard=True)


def admin_withdrawals_list_keyboard(
    page: int = 1, total_pages: int = 1
) -> ReplyKeyboardMarkup:
    """
    Keyboard for withdrawals list with pagination.

    Args:
        page: Current page number
        total_pages: Total number of pages

    Returns:
        ReplyKeyboardMarkup with pagination
    """
    builder = ReplyKeyboardBuilder()

    # Navigation
    nav_buttons = []
    if total_pages > 1:
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="Следующая ➡"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="◀️ К карточке"),
        KeyboardButton(text="👑 Админ-панель")
    )

    return builder.as_markup(resize_keyboard=True)


def admin_wallet_history_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for wallet change history.

    Returns:
        ReplyKeyboardMarkup with back navigation
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="◀️ К карточке"),
        KeyboardButton(text="👑 Админ-панель")
    )
    return builder.as_markup(resize_keyboard=True)


def admin_withdrawal_settings_keyboard(
    is_daily_limit_enabled: bool = True,
    auto_withdrawal_enabled: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Admin withdrawal settings keyboard (Reply version).

    Args:
        is_daily_limit_enabled: Whether daily limit is enabled
        auto_withdrawal_enabled: Whether auto-withdrawal is enabled

    Returns:
        ReplyKeyboardMarkup with withdrawal settings options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="💵 Изм. Мин. Вывод"))
    builder.row(KeyboardButton(text="🛡 Изм. Дневной Лимит"))
    builder.row(KeyboardButton(text="💸 Изм. Комиссию (%)"))

    limit_text = "🔴 Выключить Лимит" if is_daily_limit_enabled else "🟢 Включить Лимит"
    builder.row(KeyboardButton(text=limit_text))

    auto_text = "🔴 Выключить Авто-вывод" if auto_withdrawal_enabled else "🟢 Включить Авто-вывод"
    builder.row(KeyboardButton(text=auto_text))

    builder.row(
        KeyboardButton(text="◀️ Назад к выводам"),
        KeyboardButton(text="👑 Админ-панель")
    )

    return builder.as_markup(resize_keyboard=True)


def admin_withdrawal_history_pagination_keyboard(
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Admin withdrawal history pagination keyboard (Reply version).

    Args:
        page: Current page number
        total_pages: Total number of pages

    Returns:
        ReplyKeyboardMarkup with pagination buttons
    """
    builder = ReplyKeyboardBuilder()

    # Navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(KeyboardButton(text="⬅️ Пред. страница выводов"))
    if page < total_pages:
        nav_buttons.append(KeyboardButton(text="Вперёд страница выводов ➡️"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="◀️ Назад"),
        KeyboardButton(text="👑 Админ-панель")
    )

    return builder.as_markup(resize_keyboard=True)


# ============================================================================
# INQUIRY KEYBOARDS (Admin handling user questions)
# ============================================================================


def admin_inquiry_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin inquiry management menu.

    Returns:
        ReplyKeyboardMarkup with inquiry options
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📬 Новые обращения"))
    builder.row(KeyboardButton(text="📋 Мои обращения"))
    builder.row(KeyboardButton(text="✅ Закрытые обращения"))
    builder.row(KeyboardButton(text="👑 Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def admin_inquiry_list_keyboard(
    inquiries: list,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Keyboard with inquiry buttons for admin selection.

    Args:
        inquiries: List of UserInquiry objects
        page: Current page
        total_pages: Total pages

    Returns:
        ReplyKeyboardMarkup with inquiry selection
    """
    builder = ReplyKeyboardBuilder()

    for inquiry in inquiries:
        # Show user info and question preview
        username = inquiry.user.username or f"ID:{inquiry.user_id}"
        preview = inquiry.initial_question[:30] + "..."
        builder.row(
            KeyboardButton(text=f"📩 #{inquiry.id} {username}: {preview}")
        )

    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(KeyboardButton(text="⬅️ Пред. стр."))
    if page < total_pages:
        nav_buttons.append(KeyboardButton(text="➡️ След. стр."))
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(KeyboardButton(text="🔄 Обновить список"))
    builder.row(KeyboardButton(text="◀️ Назад к обращениям"))
    return builder.as_markup(resize_keyboard=True)


def admin_inquiry_detail_keyboard(
    is_assigned: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Keyboard for viewing specific inquiry.

    Args:
        is_assigned: Whether inquiry is assigned to current admin

    Returns:
        ReplyKeyboardMarkup with inquiry actions
    """
    builder = ReplyKeyboardBuilder()

    if not is_assigned:
        builder.row(KeyboardButton(text="✋ Взять в работу"))
    else:
        builder.row(KeyboardButton(text="💬 Ответить пользователю"))
        builder.row(KeyboardButton(text="✅ Закрыть обращение"))

    builder.row(KeyboardButton(text="◀️ Назад к списку"))
    builder.row(KeyboardButton(text="👑 Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def admin_inquiry_response_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard while admin is writing response.

    Returns:
        ReplyKeyboardMarkup with cancel option
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    builder.row(KeyboardButton(text="◀️ Назад к обращению"))
    return builder.as_markup(resize_keyboard=True)
