"""
ROI Corridor input handlers.

Handles input for min/max percentages, fixed percentage, and reason.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.validators.common import validate_amount
from bot.keyboards.reply import admin_roi_applies_to_keyboard
from bot.states.admin import AdminRoiCorridorStates


async def process_reason_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process optional human-readable reason for corridor change.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    # Import here to avoid circular dependency
    from bot.handlers.admin.roi_corridor.corridor_confirmation import show_confirmation

    raw_text = (message.text or "").strip()
    if raw_text.lower() in {"пропустить", "skip"}:
        reason = None
    else:
        reason = raw_text or None

    await state.update_data(reason=reason)

    # After capturing reason, show confirmation summary
    await show_confirmation(message, state, session, data)


async def process_min_input(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Process minimum percentage input.

    Args:
        message: Message object
        state: FSM context
    """
    if not message.text:
        await message.answer("❌ Пожалуйста, введите число.")
        return

    # Validate amount (percentage)
    is_valid, roi_min, error_msg = validate_amount(
        message.text.strip(),
        min_amount=Decimal("0")
    )

    if not is_valid:
        await message.answer(
            f"❌ {error_msg}\n\n"
            "Введите число (например: `0.8`):",
            parse_mode="Markdown",
        )
        return

    # Convert Decimal to float for JSON serialization in FSM state
    await state.update_data(roi_min=float(roi_min))
    await state.set_state(AdminRoiCorridorStates.entering_max)
    await message.answer(
        f"**Минимум:** {roi_min}%\n\n"
        "**Введите максимальный процент коридора**\n\n"
        "Например: `10` (для 10% в период)\n\n"
        "Это верхняя граница случайного процента.",
        parse_mode="Markdown",
    )


async def process_max_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process maximum percentage input.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    if not message.text:
        await message.answer("❌ Пожалуйста, введите число.")
        return

    # Validate amount (percentage)
    is_valid, roi_max, error_msg = validate_amount(
        message.text.strip(),
        min_amount=Decimal("0")
    )

    if not is_valid:
        await message.answer(
            f"❌ {error_msg}\n\n"
            "Введите число (например: `10`):",
            parse_mode="Markdown",
        )
        return

    state_data = await state.get_data()
    roi_min = Decimal(str(state_data["roi_min"]))  # Convert back from float

    if roi_max <= roi_min:
        await message.answer(
            f"❌ Максимум ({roi_max}%) должен быть больше "
            f"минимума ({roi_min}%).\n\n"
            "Введите максимальный процент заново:",
        )
        return

    # Convert Decimal to float for JSON serialization in FSM state
    await state.update_data(roi_max=float(roi_max))

    # After entering corridor, ask when to apply
    await state.set_state(AdminRoiCorridorStates.selecting_applies_to)
    await message.answer(
        f"**Коридор:** {roi_min}% - {roi_max}%\n\n"
        "**Шаг 2/4: Когда применить изменения?**\n\n"
        "⚡️ **Текущая сессия** - изменения применятся к ближайшему "
        "начислению всех пользователей (в течение периода начисления)\n\n"
        "⏭ **Следующая сессия** - изменения применятся через одно "
        "начисление",
        parse_mode="Markdown",
        reply_markup=admin_roi_applies_to_keyboard(),
    )


async def process_fixed_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process fixed percentage input.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    if not message.text:
        await message.answer("❌ Пожалуйста, введите число.")
        return

    # Validate amount (percentage)
    is_valid, roi_fixed, error_msg = validate_amount(
        message.text.strip(),
        min_amount=Decimal("0")
    )

    if not is_valid:
        await message.answer(
            f"❌ {error_msg}\n\n"
            "Введите число (например: `5.5`):",
            parse_mode="Markdown",
        )
        return

    # Convert Decimal to float for JSON serialization in FSM state
    await state.update_data(roi_fixed=float(roi_fixed))

    # After entering fixed rate, ask when to apply
    await state.set_state(AdminRoiCorridorStates.selecting_applies_to)
    await message.answer(
        f"**Фиксированный процент:** {roi_fixed}%\n\n"
        "**Шаг 2/3: Когда применить изменения?**\n\n"
        "⚡️ **Текущая сессия** - изменения применятся к ближайшему "
        "начислению всех пользователей (в течение периода начисления)\n\n"
        "⏭ **Следующая сессия** - изменения применятся через одно "
        "начисление",
        parse_mode="Markdown",
        reply_markup=admin_roi_applies_to_keyboard(),
    )


# Handler registration function
def register_corridor_input_handlers(router):
    """Register corridor input handlers to the router."""
    router.message.register(
        process_reason_input,
        AdminRoiCorridorStates.entering_reason
    )
    router.message.register(
        process_min_input,
        AdminRoiCorridorStates.entering_min
    )
    router.message.register(
        process_max_input,
        AdminRoiCorridorStates.entering_max
    )
    router.message.register(
        process_fixed_input,
        AdminRoiCorridorStates.entering_fixed
    )
