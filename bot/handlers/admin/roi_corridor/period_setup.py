"""
ROI Corridor period setup.

Handles configuration of the accrual period for ROI.
"""

from __future__ import annotations

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.roi_corridor_service import RoiCorridorService
from bot.handlers.admin.roi_corridor.utils import notify_other_admins_period
from bot.keyboards.reply import admin_roi_confirmation_keyboard
from bot.states.admin import AdminRoiCorridorStates
from bot.utils.admin_utils import clear_state_preserve_admin_token


async def start_period_setup(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Start period setup flow.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    corridor_service = RoiCorridorService(session)
    current_period = await corridor_service.get_accrual_period_hours()

    await state.set_state(AdminRoiCorridorStates.setting_period)
    await message.answer(
        f"⏱ **Настройка периода начисления**\n\n"
        f"**Текущий период:** {current_period} часов\n\n"
        "Введите новый период в часах (от 1 до 24):\n\n"
        "Например: `6` (для начисления каждые 6 часов)\n\n"
        "⚠️ **Важно:** Период применяется индивидуально для каждого "
        "пользователя от момента создания его депозита.",
        parse_mode="Markdown",
    )


async def process_period_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process period input.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    try:
        hours = int(message.text.strip())
        if hours < 1 or hours > 24:
            raise ValueError("Out of range")
    except Exception:
        await message.answer(
            "❌ Неверный формат. Введите целое число от 1 до 24:",
        )
        return

    # Save to state and show confirmation
    await state.update_data(new_period_hours=hours)
    await state.set_state(AdminRoiCorridorStates.confirming_period)

    await message.answer(
        f"⚠️ **Подтверждение изменений**\n\n"
        f"Новый период начисления: **{hours} часов**\n\n"
        "❗️ **ВНИМАНИЕ:**\n"
        "Изменения применятся к следующему циклу начисления для всех депозитов!\n\n"
        "Подтвердить?",
        parse_mode="Markdown",
        reply_markup=admin_roi_confirmation_keyboard(),
    )


async def process_period_confirmation(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process period change confirmation.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    # Import here to avoid circular dependency
    from bot.handlers.admin.roi_corridor.menu import show_roi_corridor_menu

    if "Нет" in message.text or "отменить" in message.text.lower():
        await clear_state_preserve_admin_token(state)
        await message.answer("❌ Изменения отменены.")
        await show_roi_corridor_menu(message, session, **data)
        return

    if "Да" not in message.text and "применить" not in message.text.lower():
        await message.answer(
            "❌ Неверный ответ. Выберите из предложенных вариантов.",
            reply_markup=admin_roi_confirmation_keyboard(),
        )
        return

    state_data = await state.get_data()
    hours = state_data.get("new_period_hours")
    admin_id = data.get("admin_id")

    if not hours or not admin_id:
        await clear_state_preserve_admin_token(state)
        await message.answer("❌ Ошибка: данные потеряны")
        return

    corridor_service = RoiCorridorService(session)
    success, error = await corridor_service.set_accrual_period_hours(
        hours, admin_id
    )

    if success:
        await message.answer(
            f"✅ **Период начисления обновлён!**\n\n"
            f"Новый период: {hours} часов\n\n"
            "Изменения вступят в силу при следующем автоматическом начислении.",
            parse_mode="Markdown",
        )

        # Notify other admins
        await notify_other_admins_period(session, admin_id, hours)

        logger.info(
            "Accrual period updated",
            extra={"hours": hours, "admin_id": admin_id},
        )
    else:
        await message.answer(f"❌ Ошибка: {error}")

    await clear_state_preserve_admin_token(state)
    await show_roi_corridor_menu(message, session, **data)


# Handler registration function
def register_period_setup_handlers(router):
    """Register period setup handlers to the router."""
    router.message.register(
        start_period_setup,
        F.text == "⏱ Настроить период начисления"
    )
    router.message.register(
        process_period_input,
        AdminRoiCorridorStates.setting_period
    )
    router.message.register(
        process_period_confirmation,
        AdminRoiCorridorStates.confirming_period
    )
