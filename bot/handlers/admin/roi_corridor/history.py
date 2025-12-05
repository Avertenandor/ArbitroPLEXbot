"""
ROI Corridor history viewing.

Handles displaying change history for corridor configurations.
"""

from __future__ import annotations

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.services.roi_corridor_service import RoiCorridorService
from bot.handlers.admin.roi_corridor.utils import check_cancel_or_back
from bot.keyboards.reply import (
    admin_roi_corridor_menu_keyboard,
    admin_roi_level_select_keyboard,
)
from bot.states.admin import AdminRoiCorridorStates
from bot.utils.admin_utils import clear_state_preserve_admin_token


async def start_history_view(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Start history viewing flow.

    Args:
        message: Message object
        state: FSM context
    """
    await state.set_state(AdminRoiCorridorStates.viewing_history_level)
    await message.answer(
        "Выберите уровень для просмотра истории изменений:",
        reply_markup=admin_roi_level_select_keyboard(),
    )


async def show_level_history(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show history for selected level.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    # Check for navigation
    if await check_cancel_or_back(message, state, session, **data):
        return

    # Extract level number
    try:
        level = int(message.text.split()[-1])
        if level < 1 or level > 5:
            raise ValueError
    except Exception:
        await message.answer(
            "❌ Неверный уровень. Выберите от 1 до 5.",
            reply_markup=admin_roi_level_select_keyboard(),
        )
        return

    corridor_service = RoiCorridorService(session)
    history = await corridor_service.history_repo.get_history_for_level(
        level, limit=20
    )

    if not history:
        await message.answer(
            f"📜 История изменений для уровня {level} пуста.",
            reply_markup=admin_roi_corridor_menu_keyboard(),
        )
        await clear_state_preserve_admin_token(state)
        return

    text = f"📜 **История изменений - Уровень {level}**\n\n"

    admin_repo = AdminRepository(session)

    for record in history[:10]:
        mode_text = "Custom" if record.mode == "custom" else "Поровну"
        applies_text = (
            "текущая" if record.applies_to == "current" else "следующая"
        )

        if record.mode == "custom":
            config_text = f"{record.roi_min}% - {record.roi_max}%"
        else:
            config_text = f"{record.roi_fixed}%"

        # Build admin info: @username (ID: 123) or "Система"
        if record.changed_by_admin_id:
            admin = await admin_repo.get_by_id(record.changed_by_admin_id)
            if admin and admin.username:
                admin_label = f"@{admin.username} (ID: {admin.telegram_id})"
            elif admin:
                admin_label = f"Admin (ID: {admin.telegram_id})"
            else:
                admin_label = f"Admin ID: {record.changed_by_admin_id}"
        else:
            admin_label = "Система"

        reason = record.reason
        reason_block = f"   💬 Причина: {reason}\n" if reason else ""

        text += (
            f"📅 {record.changed_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"   Режим: {mode_text}\n"
            f"   Значение: {config_text}\n"
            f"   Применено к: {applies_text}\n"
            f"   Изменил: {admin_label}\n"
            f"{reason_block}\n"
        )

    if len(history) > 10:
        text += f"... и еще {len(history) - 10} записей"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_roi_corridor_menu_keyboard(),
    )
    await clear_state_preserve_admin_token(state)


# Handler registration function
def register_history_handlers(router):
    """Register history handlers to the router."""
    router.message.register(
        start_history_view,
        F.text == "📜 История изменений"
    )
    router.message.register(
        show_level_history,
        AdminRoiCorridorStates.viewing_history_level
    )
