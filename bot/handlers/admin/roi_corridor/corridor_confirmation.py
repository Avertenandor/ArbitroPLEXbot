"""
ROI Corridor confirmation and saving.

Handles confirmation display and final save operation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.roi_corridor_service import RoiCorridorService
from bot.handlers.admin.roi_corridor.utils import notify_other_admins
from bot.keyboards.reply import admin_roi_confirmation_keyboard
from bot.states.admin import AdminRoiCorridorStates
from bot.utils.admin_utils import clear_state_preserve_admin_token


async def show_confirmation(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    data: dict,
) -> None:
    """
    Show confirmation screen with settings summary.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    state_data = await state.get_data()
    level = state_data["level"]
    mode = state_data["mode"]
    mode_text = state_data["mode_text"]
    state_data["applies_to"]
    applies_text = state_data["applies_text"]

    if mode == "custom":
        roi_min = state_data["roi_min"]
        roi_max = state_data["roi_max"]
        config_text = f"**Коридор:** {roi_min}% - {roi_max}%"
    else:
        roi_fixed = state_data["roi_fixed"]
        config_text = f"**Фиксированный:** {roi_fixed}%"

    reason = state_data.get("reason")

    # Validate and get warnings
    corridor_service = RoiCorridorService(session)
    warning = ""

    if mode == "custom":
        # Convert float back to Decimal for validation
        roi_min_decimal = Decimal(str(state_data["roi_min"]))
        roi_max_decimal = Decimal(str(state_data["roi_max"]))
        needs_confirm, warning_msg = (
            await corridor_service.validate_corridor_settings(
                roi_min_decimal, roi_max_decimal
            )
        )
        if needs_confirm and warning_msg:
            warning = f"\n\n{warning_msg}\n\n⚠️ **Требуется подтверждение!**"
    else:
        roi_fixed_float = state_data["roi_fixed"]
        if roi_fixed_float < 0.5 or roi_fixed_float > 20:
            warning = (
                f"\n\n⚠️ **ПРЕДУПРЕЖДЕНИЕ:** "
                f"Экстремальное значение: {roi_fixed_float}%\n"
                "(Рекомендуется: 0.5% - 20%)\n\n"
                "⚠️ **Требуется подтверждение!**"
            )

    reason_block = ""
    if reason:
        reason_block = f"\n**Причина:** {reason}"

    text = (
        "📋 **Подтверждение настроек**\n\n"
        f"**Уровень:** {level}\n"
        f"**Режим:** {mode_text}\n"
        f"{config_text}\n"
        f"**Применить к:** {applies_text}"
        f"{reason_block}"
        f"{warning}\n\n"
        "Подтвердите изменения:"
    )

    await state.set_state(AdminRoiCorridorStates.confirming)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_roi_confirmation_keyboard(),
    )


async def process_confirmation(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process confirmation.

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
    admin_id = data.get("admin_id")

    if not admin_id:
        await clear_state_preserve_admin_token(state)
        await message.answer("❌ Ошибка: admin_id не найден")
        return

    corridor_service = RoiCorridorService(session)

    # Convert float back to Decimal for service call
    roi_min_val = state_data.get("roi_min")
    roi_max_val = state_data.get("roi_max")
    roi_fixed_val = state_data.get("roi_fixed")
    reason = state_data.get("reason")

    success, error = await corridor_service.set_corridor(
        level=state_data["level"],
        mode=state_data["mode"],
        roi_min=Decimal(str(roi_min_val)) if roi_min_val is not None else None,
        roi_max=Decimal(str(roi_max_val)) if roi_max_val is not None else None,
        roi_fixed=Decimal(str(roi_fixed_val)) if roi_fixed_val is not None else None,
        admin_id=admin_id,
        applies_to=state_data["applies_to"],
        reason=reason,
    )

    if success:
        level = state_data["level"]
        mode_text = state_data["mode_text"]
        applies_text = state_data["applies_text"]

        if state_data["mode"] == "custom":
            config_text = (
                f"{state_data['roi_min']}% - {state_data['roi_max']}%"
            )
        else:
            config_text = f"{state_data['roi_fixed']}%"

        await message.answer(
            f"✅ **Настройки успешно применены!**\n\n"
            f"**Уровень:** {level}\n"
            f"**Режим:** {mode_text}\n"
            f"**Значение:** {config_text}\n"
            f"**Применено к:** {applies_text}",
            parse_mode="Markdown",
        )

        # Notify other admins
        await notify_other_admins(
            session, admin_id, level, mode_text, config_text, applies_text
        )

        logger.info(
            "Corridor settings updated",
            extra={
                "level": level,
                "mode": state_data["mode"],
                "applies_to": state_data["applies_to"],
                "admin_id": admin_id,
            },
        )

        # Check if we should redirect back to level management
        if state_data.get("from_level_management"):
            # Import here to avoid circular dependency
            from bot.handlers.admin.deposit_management import (
                show_level_actions_for_level,
            )

            await clear_state_preserve_admin_token(state)
            await show_level_actions_for_level(message, session, state, level, **data)
            return

    else:
        await message.answer(f"❌ Ошибка: {error}")

    await clear_state_preserve_admin_token(state)
    await show_roi_corridor_menu(message, session, **data)


# Handler registration function
def register_corridor_confirmation_handlers(router):
    """Register corridor confirmation handlers to the router."""
    router.message.register(
        process_confirmation,
        AdminRoiCorridorStates.confirming
    )
