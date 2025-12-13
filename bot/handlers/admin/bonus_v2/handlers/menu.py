"""
Menu handlers for bonus management.

Handles main menu entry, navigation, and back buttons.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bonus_service import BonusService
from bot.handlers.admin.utils.admin_checks import (
    get_admin_or_deny,
    get_admin_or_deny_callback,
)
from bot.keyboards.reply import get_admin_keyboard_from_data
from bot.utils.formatters import format_balance, format_usdt

from ..helpers import get_role_display, get_role_permissions
from ..keyboards import bonus_main_menu_keyboard
from ..states import BonusStates


router = Router(name="bonus_menu")


# ============ MAIN MENU ============


@router.message(StateFilter("*"), F.text == "🎁 Бонусы")
async def open_bonus_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Открыть главное меню бонусов."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(BonusStates.menu)

    bonus_service = BonusService(session)
    stats = await bonus_service.get_global_bonus_stats()

    role_display = get_role_display(admin.role)
    permissions = get_role_permissions(admin.role)

    # Формируем подсказку по правам
    perm_text = []
    if permissions["can_grant"]:
        perm_text.append("✅ начисление")
    if permissions["can_cancel_any"]:
        perm_text.append("✅ отмена любых")
    elif permissions["can_cancel_own"]:
        perm_text.append("✅ отмена своих")
    if permissions["can_view"]:
        perm_text.append("✅ просмотр")

    total_granted = format_balance(stats.get('total_granted', 0), decimals=2)
    last_24h = format_balance(stats.get('last_24h', 0), decimals=2)
    text = (
        f"🎁 **Управление бонусами**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Вы: {role_display}\n"
        f"🔐 Права: {', '.join(perm_text)}\n\n"
        f"📊 **Общая статистика:**\n"
        f"├ 💰 Всего начислено: **{total_granted}** USDT\n"
        f"├ 🟢 Активных: **{stats.get('active_count', 0)}** "
        f"бонусов\n"
        f"├ 📅 За 24 часа: **{last_24h}** USDT\n"
        f"└ 📋 Всего записей: **{stats.get('total_count', 0)}**\n\n"
        f"_Выберите действие:_"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=bonus_main_menu_keyboard(admin.role),
    )


# ============ BACK TO ADMIN ============


@router.message(BonusStates.menu, F.text == "◀️ Назад в админку")
async def back_to_admin(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Вернуться в админ-панель."""
    from bot.utils.admin_utils import clear_state_preserve_admin_token

    await clear_state_preserve_admin_token(state)
    await message.answer(
        "👑 Возвращаюсь в админ-панель...",
        reply_markup=get_admin_keyboard_from_data(data),
    )


@router.callback_query(F.data == "bonus_back_to_menu")
async def callback_back_to_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Вернуться в меню бонусов."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    role = admin.role if admin else "admin"

    await state.set_state(BonusStates.menu)
    await callback.message.edit_text("◀️ Возврат в меню бонусов...")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=bonus_main_menu_keyboard(role),
    )
    await callback.answer()
