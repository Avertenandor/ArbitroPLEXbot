"""
Help command handler.

This module provides the /help command for ArbitroPLEXbot.
Shows brief information about the bot, available commands, and navigation.
"""

import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.keyboards.reply import main_menu_reply_keyboard


logger = logging.getLogger(__name__)


router = Router(name="help")


@router.message(Command("help"))
async def cmd_help(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle /help command.

    Shows brief information about the bot:
    - What the bot does (arbitrage platform interface)
    - Main commands (/start, /help)
    - Where to find: FAQ, Support, Instructions
    - Navigation back to main menu

    Args:
        message: Telegram message
        session: Database session
        state: FSM state context
        **data: Additional handler data (user, is_admin, etc.)
    """
    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)

    # Clear any active FSM state
    await state.clear()

    # Get blacklist info for proper menu
    blacklist_entry = None
    if user:
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        except Exception as e:
            logger.error(
                "Failed to check blacklist status for user %s: %s",
                user.telegram_id,
                e,
                exc_info=True
            )

    help_text = (
        "ℹ️ *Справка ArbitroPLEXbot*\n\n"
        "*ArbitroPLEXbot* — интерфейс для доступа к арбитражной системе на блокчейне BSC.\n\n"
        "*Основные команды:*\n"
        "• /start — Начать работу / Регистрация\n"
        "• /help — Показать эту справку\n\n"
        "*Полезные разделы:*\n"
        "• 💬 Поддержка — Создать обращение\n"
        "• ❓ FAQ — Частые вопросы\n"
        "• 📖 Инструкции — Руководство по использованию\n\n"
        "Используйте кнопки меню для навигации."
    )

    await message.answer(
        help_text,
        parse_mode="Markdown",
        reply_markup=main_menu_reply_keyboard(
            user=user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin
        ),
    )


@router.message(F.text == "ℹ️ Помощь")
async def handle_help_button_old(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle old "ℹ️ Помощь" button press (backward compatibility).
    Redirects to the main help submenu.
    """
    from bot.handlers.menu.help_submenu import show_help_submenu
    await show_help_submenu(message, session, state, **data)
