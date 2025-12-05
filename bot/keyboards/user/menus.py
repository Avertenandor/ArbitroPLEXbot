"""
Basic menu keyboards module.

This module contains standard menu keyboards for various user actions:
- Balance menu
- Deposit menu
- Withdrawal menu
- Referral menu
- Settings menu
- Profile menu
- Contact management menus
- Wallet menu
- Support menu
- Notification settings
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


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
            level_info.get("status_text", "")

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
        KeyboardButton(text="🌳 Моя структура"),
        KeyboardButton(text="💰 Мой заработок"),
    )
    builder.row(
        KeyboardButton(text="📊 Статистика рефералов"),
        KeyboardButton(text="📈 Аналитика"),
    )
    builder.row(
        KeyboardButton(text="🏆 ТОП партнёров"),
        KeyboardButton(text="📢 Промо-материалы"),
    )
    builder.row(
        KeyboardButton(text="💬 Написать спонсору"),
        KeyboardButton(text="📬 Входящие от рефералов"),
    )
    builder.row(
        KeyboardButton(text="👤 Кто меня пригласил"),
        KeyboardButton(text="📋 Скопировать ссылку"),
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


def instructions_keyboard(
    levels_status: dict[int, dict] | None = None,
) -> ReplyKeyboardMarkup:
    """
    Instructions keyboard with deposit levels and detail option.

    Args:
        levels_status: Optional dict with level statuses from DepositValidationService.get_available_levels()

    Returns:
        ReplyKeyboardMarkup with instructions options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📖 Подробная инструкция"),
    )

    # Default amounts if statuses not provided
    default_amounts = {1: 10, 2: 50, 3: 100, 4: 150, 5: 300}

    for level in [1, 2, 3, 4, 5]:
        if levels_status and level in levels_status:
            level_info = levels_status[level]
            amount = level_info["amount"]
            status = level_info["status"]

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


def earnings_dashboard_keyboard() -> ReplyKeyboardMarkup:
    """
    Earnings dashboard keyboard.

    Returns:
        ReplyKeyboardMarkup with earnings dashboard options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💸 Вывести средства"),
    )
    builder.row(
        KeyboardButton(text="📜 История операций"),
    )
    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)


# ============================================================================
# SUBMENU KEYBOARDS (New organized structure)
# ============================================================================


def finances_submenu_keyboard() -> ReplyKeyboardMarkup:
    """
    Finances submenu keyboard.

    Contains all financial operations:
    - Deposit
    - Withdrawal
    - Balance overview
    - Earnings dashboard

    Returns:
        ReplyKeyboardMarkup with finances options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="💰 Депозит"),
        KeyboardButton(text="💸 Вывод"),
    )

    builder.row(
        KeyboardButton(text="📈 Мой заработок"),
        KeyboardButton(text="📊 Мои средства"),
    )

    builder.row(
        KeyboardButton(text="◀️ Назад"),
    )

    return builder.as_markup(resize_keyboard=True)


def cabinet_submenu_keyboard() -> ReplyKeyboardMarkup:
    """
    User cabinet submenu keyboard.

    Contains user's portfolio and reports:
    - Active deposits
    - Transaction history
    - Calculator
    - Earnings dashboard

    Returns:
        ReplyKeyboardMarkup with cabinet options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📦 Мои депозиты"),
        KeyboardButton(text="📜 История операций"),
    )

    builder.row(
        KeyboardButton(text="📊 Калькулятор"),
        KeyboardButton(text="💰 Мой заработок"),
    )

    builder.row(
        KeyboardButton(text="◀️ Назад"),
    )

    return builder.as_markup(resize_keyboard=True)


def help_submenu_keyboard() -> ReplyKeyboardMarkup:
    """
    Help submenu keyboard.

    Contains all help and support options:
    - FAQ
    - Instructions
    - Rules
    - Support contact
    - Back to main menu

    Returns:
        ReplyKeyboardMarkup with help options
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="❓ FAQ"),
        KeyboardButton(text="📖 Инструкции"),
    )

    builder.row(
        KeyboardButton(text="📋 Правила"),
        KeyboardButton(text="✉️ Написать в поддержку"),
    )

    builder.row(
        KeyboardButton(text="📊 Главное меню"),
    )

    return builder.as_markup(resize_keyboard=True)
