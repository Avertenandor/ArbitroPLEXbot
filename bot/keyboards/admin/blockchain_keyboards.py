"""
Blockchain settings keyboards for admin panel.

Contains keyboards for managing blockchain provider settings and auto-switching.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def blockchain_settings_keyboard(
    active_provider: str,
    is_auto_switch: bool,
    is_super_admin: bool = False,
) -> ReplyKeyboardMarkup:
    """
    Blockchain settings keyboard with provider selection and auto-switch toggle.

    Args:
        active_provider: Name of currently active blockchain provider
                        ("quicknode", "nodereal", or "nodereal2")
        is_auto_switch: Whether automatic provider switching is enabled
        is_super_admin: Whether the user is a super admin (for NodeReal2 access)

    Returns:
        ReplyKeyboardMarkup with blockchain configuration options
    """
    builder = ReplyKeyboardBuilder()

    # Normalize provider name for comparison
    active_provider_lower = active_provider.lower()

    # Provider buttons with checkmark for active one
    quicknode_text = (
        "✅ QuickNode"
        if active_provider_lower == "quicknode"
        else "QuickNode"
    )
    nodereal_text = (
        "✅ NodeReal"
        if active_provider_lower == "nodereal"
        else "NodeReal"
    )

    builder.row(
        KeyboardButton(text=quicknode_text),
        KeyboardButton(text=nodereal_text),
    )

    # NodeReal2 button - only for super admins
    if is_super_admin:
        nodereal2_text = (
            "✅ NodeReal2 (резерв)"
            if active_provider_lower == "nodereal2"
            else "🔒 NodeReal2 (резерв)"
        )
        builder.row(KeyboardButton(text=nodereal2_text))

    # Auto-switch toggle button
    auto_switch_text = (
        "✅ Авто-смена ВКЛ"
        if is_auto_switch
        else "❌ Авто-смена ВЫКЛ"
    )
    builder.row(KeyboardButton(text=auto_switch_text))

    # Utility buttons
    builder.row(KeyboardButton(text="🔄 Обновить статус"))
    builder.row(KeyboardButton(text="◀️ Назад в админку"))

    return builder.as_markup(resize_keyboard=True)
