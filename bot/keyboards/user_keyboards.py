"""
User-related reply keyboards.

This module contains all keyboard builders for user-facing features.
Separated from admin keyboards for better code organization.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger

from app.models.blacklist import Blacklist, BlacklistActionType
from app.models.user import User


def main_menu_reply_keyboard(
    user: User | None = None,
    blacklist_entry: Blacklist | None = None,
    is_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Main menu reply keyboard.

    Conditionally shows buttons based on user status (e.g., blocked, admin, unregistered).

    Args:
        user: The current user object (optional). If None, shows reduced menu for unregistered users.
        blacklist_entry: The user's blacklist entry, if any (optional).
        is_admin: Whether the user is an admin (optional).

    Returns:
        ReplyKeyboardMarkup with main menu buttons
    """
    # Safely access telegram_id
    user_id = user.id if user else None

    # Fix for AttributeError: 'User' object has no attribute 'telegram_id'
    # In fallback handler, message.from_user is a Telegram User object (aiogram),
    # which has 'id', NOT 'telegram_id'.
    # Our database User model (app.models.user) has 'telegram_id'.
    # We need to handle both cases.
    telegram_id = None
    if user:
        if hasattr(user, 'telegram_id'):
            telegram_id = user.telegram_id
        elif hasattr(user, 'id'):
            telegram_id = user.id

    logger.debug(
        f"[KEYBOARD] main_menu_reply_keyboard called: "
        f"user_id={user_id}, telegram_id={telegram_id}, "
        f"is_admin={is_admin}, "
        f"blacklist_active={blacklist_entry.is_active if blacklist_entry else False}"
    )

    builder = ReplyKeyboardBuilder()

    # If user is blocked (with appeal option), show only appeal button
    if (
        user
        and blacklist_entry
        and blacklist_entry.is_active
        and blacklist_entry.action_type == BlacklistActionType.BLOCKED
    ):
        # Keep this on INFO as it's a rare security event
        logger.info(f"[KEYBOARD] User {telegram_id} is blocked, showing appeal button only")
        builder.row(
            KeyboardButton(text="📝 Подать апелляцию"),
        )
    elif user is None:
        # Reduced menu for unregistered users
        logger.debug(f"[KEYBOARD] Building reduced menu for unregistered user {telegram_id}")
        builder.row(
            KeyboardButton(text="📖 Инструкции"),
        )
        builder.row(
            KeyboardButton(text="💬 Поддержка"),
        )
        builder.row(
            KeyboardButton(text="📝 Регистрация"),
        )
    else:
        # Standard menu for registered users
        logger.debug(f"[KEYBOARD] Building standard menu for user {telegram_id}")
        builder.row(
            KeyboardButton(text="💰 Депозит"),
            KeyboardButton(text="💸 Вывод"),
        )
        builder.row(
            KeyboardButton(text="📦 Мои депозиты"),
            KeyboardButton(text="🔄 Обновить депозит"),
        )
        builder.row(
            KeyboardButton(text="👥 Рефералы"),
            KeyboardButton(text="📊 Баланс"),
        )
        builder.row(
            KeyboardButton(text="💬 Поддержка"),
            KeyboardButton(text="⚙️ Настройки"),
        )
        builder.row(
            KeyboardButton(text="📖 Инструкции"),
            KeyboardButton(text="📜 История операций"),
        )
        builder.row(
            KeyboardButton(text="📊 Калькулятор"),
            KeyboardButton(text="🔐 Получить финпароль"),
        )
        builder.row(
            KeyboardButton(text="🔑 Восстановить финпароль"),
        )
        builder.row(
            KeyboardButton(text="🐰 Купить кролика"),
            KeyboardButton(text="📋 Правила"),
        )
        builder.row(
            KeyboardButton(text="🌐 Инструменты нашей экосистемы"),
        )

        # Add admin panel button for admins
        if is_admin:
            logger.info(f"[KEYBOARD] Adding admin panel button for user {telegram_id}")
            builder.row(
                KeyboardButton(text="👑 Админ-панель"),
            )

            # Add master key management button for super admin
            from app.config.settings import settings
            admin_ids = settings.get_admin_ids()
            is_super_admin_id = telegram_id and admin_ids and telegram_id == admin_ids[0]

            logger.info("[KEYBOARD] AFTER admin panel button, before master key check")
            logger.info(
                f"[KEYBOARD] Checking master key button: "
                f"telegram_id={telegram_id}, type={type(telegram_id)}, "
                f"is_super_admin_id={is_super_admin_id}"
            )
            if is_super_admin_id:
                logger.info(
                    f"[KEYBOARD] Adding master key management button "
                    f"for super admin {telegram_id}"
                )
                builder.row(
                    KeyboardButton(text="🔑 Управление мастер-ключом"),
                )
            else:
                logger.info(
                    f"[KEYBOARD] NOT adding master key button: "
                    f"telegram_id={telegram_id} != {admin_ids[0] if admin_ids else 'None'}"
                )

        # Log for non-admin case is handled by the if block above

    keyboard = builder.as_markup(resize_keyboard=True)
    logger.info(f"[KEYBOARD] Keyboard created for user {telegram_id}, buttons count: {len(keyboard.keyboard)}")
    return keyboard


def balance_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Balance menu keyboard.

    Returns:
        ReplyKeyboardMarkup with balance options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💰 Баланс"),
    )
    builder.row(
        KeyboardButton(text="📜 История операций"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def deposit_menu_keyboard(
    levels_status: dict[int, dict] | None = None,
) -> ReplyKeyboardMarkup:
    """
    Deposit menu reply keyboard with status indicators.

    Args:
        levels_status: Optional dict with level statuses from DepositValidationService.get_available_levels()

    Returns:
        ReplyKeyboardMarkup with deposit options
    """
    builder = ReplyKeyboardBuilder()

    # Default amounts if statuses not provided
    default_amounts = {1: 10, 2: 50, 3: 100, 4: 150, 5: 300}

    for level in [1, 2, 3, 4, 5]:
        if levels_status and level in levels_status:
            level_info = levels_status[level]
            amount = level_info["amount"]
            status = level_info["status"]
            status_text = level_info.get("status_text", "")

            # Build button text with status indicator
            if status == "active":
                button_text = f"✅ Level {level} ({amount} USDT) - Активен"
            elif status == "available":
                button_text = f"💰 Пополнить Level {level} ({amount} USDT)"
            else:
                # unavailable - show reason in button
                error = level_info.get("error", "")
                if "необходимо сначала купить" in error:
                    button_text = f"🔒 Level {level} ({amount} USDT) - Нет предыдущего"
                elif "временно недоступен" in error:
                    button_text = f"🔒 Level {level} ({amount} USDT) - Закрыт"
                else:
                    button_text = f"🔒 Level {level} ({amount} USDT) - Недоступен"
        else:
            # Fallback to default
            amount = default_amounts[level]
            button_text = f"💰 Пополнить Level {level} ({amount} USDT)"

        builder.row(KeyboardButton(text=button_text))

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def withdrawal_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Withdrawal menu reply keyboard.

    Returns:
        ReplyKeyboardMarkup with withdrawal options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💸 Вывести всю сумму"),
    )
    builder.row(
        KeyboardButton(text="💵 Вывести указанную сумму"),
    )
    builder.row(
        KeyboardButton(text="📜 История выводов"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def referral_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Referral menu reply keyboard.

    Returns:
        ReplyKeyboardMarkup with referral options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="👥 Мои рефералы"),
    )
    builder.row(
        KeyboardButton(text="💰 Мой заработок"),
    )
    builder.row(
        KeyboardButton(text="📊 Статистика рефералов"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def settings_menu_keyboard(language: str | None = None) -> ReplyKeyboardMarkup:
    """
    Settings menu reply keyboard.

    Args:
        language: User's preferred language (currently unused, for future i18n)

    Returns:
        ReplyKeyboardMarkup with settings options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="👤 Мой профиль"),
    )
    builder.row(
        KeyboardButton(text="💳 Мой кошелек"),
    )
    builder.row(
        KeyboardButton(text="🔔 Настройки уведомлений"),
    )
    builder.row(
        KeyboardButton(text="📝 Обновить контакты"),
    )
    builder.row(
        KeyboardButton(text="🌐 Изменить язык"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def profile_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Profile menu keyboard.

    Returns:
        ReplyKeyboardMarkup with profile options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📂 Скачать отчет"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад"),
    )

    return builder.as_markup(resize_keyboard=True)


def contact_update_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Contact update menu keyboard.

    Returns:
        ReplyKeyboardMarkup with contact update options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📞 Обновить телефон"),
    )
    builder.row(
        KeyboardButton(text="📧 Обновить email"),
    )
    builder.row(
        KeyboardButton(text="📝 Обновить оба"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад"),
        KeyboardButton(text="🏠 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def contact_input_keyboard() -> ReplyKeyboardMarkup:
    """
    Contact input keyboard with skip option.

    Returns:
        ReplyKeyboardMarkup with skip and navigation options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="⏭ Пропустить"),
    )
    builder.row(
        KeyboardButton(text="◀️ Назад"),
        KeyboardButton(text="🏠 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


# ============================================================================
# Additional user keyboards
# ============================================================================

def wallet_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Wallet menu keyboard.

    Returns:
        ReplyKeyboardMarkup with wallet options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🔄 Сменить кошелек"))
    builder.row(
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="📊 Главное меню")
    )

    return builder.as_markup(resize_keyboard=True)


def support_keyboard() -> ReplyKeyboardMarkup:
    """
    Support menu reply keyboard.

    Returns:
        ReplyKeyboardMarkup with support options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="✉️ Создать обращение"),
    )
    builder.row(
        KeyboardButton(text="📋 Мои обращения"),
    )
    builder.row(
        KeyboardButton(text="❓ FAQ"),
    )
    # Покажем и "Назад", и явную кнопку выхода в главное меню —
    # пользователи привыкли к обоим вариантам.
    builder.row(
        KeyboardButton(text="⬅ Назад"),
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def finpass_input_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for financial password input with cancel button.

    Returns:
        ReplyKeyboardMarkup with cancel option
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Отменить вывод"),
    )

    return builder.as_markup(resize_keyboard=True)


def finpass_recovery_keyboard() -> ReplyKeyboardMarkup:
    """
    Financial password recovery keyboard.

    Returns:
        ReplyKeyboardMarkup with recovery options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Отмена"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def finpass_recovery_confirm_keyboard() -> ReplyKeyboardMarkup:
    """
    Financial password recovery confirmation keyboard.

    Returns:
        ReplyKeyboardMarkup with confirm/cancel buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="✅ Отправить заявку"),
    )
    builder.row(
        KeyboardButton(text="❌ Отменить"),
    )

    return builder.as_markup(resize_keyboard=True)


def notification_settings_reply_keyboard(
    deposit_enabled: bool,
    withdrawal_enabled: bool,
    roi_enabled: bool = True,
    marketing_enabled: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Notification settings reply keyboard.

    Args:
        deposit_enabled: Whether deposit notifications are enabled
        withdrawal_enabled: Whether withdrawal notifications are enabled
        roi_enabled: Whether ROI notifications are enabled
        marketing_enabled: Whether marketing notifications are enabled

    Returns:
        ReplyKeyboardMarkup with notification toggle buttons
    """
    builder = ReplyKeyboardBuilder()

    # Deposit notifications toggle
    deposit_text = (
        "✅ Уведомления о депозитах" if deposit_enabled
        else "❌ Уведомления о депозитах"
    )
    builder.row(
        KeyboardButton(text=deposit_text),
    )

    # Withdrawal notifications toggle
    withdrawal_text = (
        "✅ Уведомления о выводах" if withdrawal_enabled
        else "❌ Уведомления о выводах"
    )
    builder.row(
        KeyboardButton(text=withdrawal_text),
    )

    # ROI notifications toggle
    roi_text = (
        "✅ Уведомления о ROI" if roi_enabled
        else "❌ Уведомления о ROI"
    )
    builder.row(
        KeyboardButton(text=roi_text),
    )

    # Marketing notifications toggle
    marketing_text = (
        "✅ Маркетинговые уведомления" if marketing_enabled
        else "❌ Маркетинговые уведомления"
    )
    builder.row(
        KeyboardButton(text=marketing_text),
    )

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def contacts_choice_keyboard() -> ReplyKeyboardMarkup:
    """
    Contacts choice keyboard for registration.

    Returns:
        ReplyKeyboardMarkup with contacts choice options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="✅ Да, оставить контакты"),
    )
    builder.row(
        KeyboardButton(text="⏭ Пропустить"),
    )

    return builder.as_markup(resize_keyboard=True)


def transaction_history_type_keyboard() -> ReplyKeyboardMarkup:
    """
    Transaction history type selection keyboard.

    Returns:
        ReplyKeyboardMarkup with transaction type buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🔄 Внутренние транзакции"),
        KeyboardButton(text="🔗 Транзакции в блокчейне"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def transaction_history_keyboard(
    current_filter: str | None = None,
    has_prev: bool = False,
    has_next: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Transaction history keyboard with filters and pagination.

    Args:
        current_filter: Current filter type (all/deposit/withdrawal/referral)
        has_prev: Whether there is a previous page
        has_next: Whether there is a next page

    Returns:
        ReplyKeyboardMarkup with filter and navigation options
    """
    builder = ReplyKeyboardBuilder()

    # Filter buttons
    builder.row(
        KeyboardButton(text="📊 Все транзакции"),
    )
    builder.row(
        KeyboardButton(text="💰 Депозиты"),
        KeyboardButton(text="💸 Выводы"),
    )
    builder.row(
        KeyboardButton(text="🎁 Реферальные"),
    )

    # Export button
    builder.row(
        KeyboardButton(text="📥 Скачать отчет (Excel)"),
    )

    # Navigation buttons
    nav_buttons = []
    if has_prev:
        nav_buttons.append(KeyboardButton(text="⬅ Предыдущая страница"))
    if has_next:
        nav_buttons.append(KeyboardButton(text="➡ Следующая страница"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="◀️ Назад"),
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def referral_list_keyboard(
    level: int = 1,
    page: int = 1,
    total_pages: int = 1,
) -> ReplyKeyboardMarkup:
    """
    Referral list keyboard with level selection and pagination.

    Args:
        level: Current referral level (1-3)
        page: Current page number
        total_pages: Total number of pages

    Returns:
        ReplyKeyboardMarkup with level selection and navigation options
    """
    builder = ReplyKeyboardBuilder()

    # Level selection buttons
    builder.row(
        KeyboardButton(text="📊 Уровень 1"),
        KeyboardButton(text="📊 Уровень 2"),
        KeyboardButton(text="📊 Уровень 3"),
    )

    # Navigation buttons (only if more than one page)
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая страница"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="➡ Следующая страница"))

        if nav_buttons:
            builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def withdrawal_history_keyboard(
    page: int = 1,
    total_pages: int = 1,
    has_withdrawals: bool = True,
) -> ReplyKeyboardMarkup:
    """
    Withdrawal history keyboard with pagination.

    Args:
        page: Current page number
        total_pages: Total number of pages
        has_withdrawals: Whether there are any withdrawals

    Returns:
        ReplyKeyboardMarkup with navigation options
    """
    builder = ReplyKeyboardBuilder()

    # Navigation buttons (only if more than one page and has withdrawals)
    if has_withdrawals and total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(KeyboardButton(text="⬅ Предыдущая страница выводов"))
        if page < total_pages:
            nav_buttons.append(KeyboardButton(text="➡ Следующая страница выводов"))

        if nav_buttons:
            builder.row(*nav_buttons)

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


def show_password_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard to show password again after registration.

    Returns:
        ReplyKeyboardMarkup with show password button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🔑 Показать пароль ещё раз"))
    builder.row(KeyboardButton(text="📊 Главное меню"))

    return builder.as_markup(resize_keyboard=True)


# ============================================================================
# АВТОРИЗАЦИЯ (PAY-TO-USE) - Reply клавиатуры
# ============================================================================

def auth_wallet_input_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for wallet input during authorization.

    Returns:
        ReplyKeyboardMarkup with cancel button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="❌ Отмена"))

    return builder.as_markup(resize_keyboard=True)


def auth_payment_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for payment confirmation during authorization.

    Returns:
        ReplyKeyboardMarkup with payment confirmation button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="✅ Я оплатил"))

    return builder.as_markup(resize_keyboard=True)


def auth_continue_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard after successful payment - continue to main menu.

    Returns:
        ReplyKeyboardMarkup with continue button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🚀 Начать работу"))

    return builder.as_markup(resize_keyboard=True)


def auth_rescan_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for deposit rescan option.

    Returns:
        ReplyKeyboardMarkup with rescan and continue buttons
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🔄 Обновить депозит"))
    builder.row(KeyboardButton(text="🚀 Продолжить (без депозита)"))

    return builder.as_markup(resize_keyboard=True)


def auth_retry_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for payment retry.

    Returns:
        ReplyKeyboardMarkup with retry button
    """
    builder = ReplyKeyboardBuilder()

    builder.row(KeyboardButton(text="🔄 Проверить снова"))

    return builder.as_markup(resize_keyboard=True)


# ============================================================================
# Utility keyboards
# ============================================================================

def confirmation_keyboard() -> ReplyKeyboardMarkup:
    """
    Simple Yes/No confirmation keyboard.

    Returns:
        ReplyKeyboardMarkup with Yes/No options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="✅ Да"),
        KeyboardButton(text="❌ Нет"),
    )

    return builder.as_markup(resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Simple cancel keyboard.

    Returns:
        ReplyKeyboardMarkup with cancel option
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❌ Отмена"),
    )

    return builder.as_markup(resize_keyboard=True)
