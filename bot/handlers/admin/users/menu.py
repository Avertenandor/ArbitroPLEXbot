"""
Admin Users Menu Handler
Handles the main users management menu and navigation
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_users_keyboard
from bot.utils.admin_utils import clear_state_preserve_admin_token


router = Router(name="admin_users_menu")


@router.message(F.text == "👥 Управление пользователями")
async def handle_admin_users_menu(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show admin users menu"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await clear_state_preserve_admin_token(state)

    await message.answer(
        "👥 **Управление пользователями**\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_users_keyboard(),
    )


@router.message(F.text == "👑 Админ-панель")
async def handle_back_to_admin_panel(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to admin panel from users menu"""
    from bot.handlers.admin.panel import handle_admin_panel_button
    await handle_admin_panel_button(message, session, **data)
