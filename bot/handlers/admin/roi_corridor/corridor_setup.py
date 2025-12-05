"""
ROI Corridor setup flow.

Handles the setup flow for corridor configuration (mode and scope selection).
"""

from __future__ import annotations

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.roi_corridor.utils import check_cancel_or_back
from bot.keyboards.reply import (
    admin_roi_applies_to_keyboard,
    admin_roi_level_select_keyboard,
    admin_roi_mode_select_keyboard,
)
from bot.states.admin import AdminRoiCorridorStates


async def start_corridor_setup(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Start corridor setup flow.

    Args:
        message: Message object
        state: FSM context
    """
    await state.set_state(AdminRoiCorridorStates.selecting_level)
    await message.answer(
        "Выберите уровень для настройки:",
        reply_markup=admin_roi_level_select_keyboard(),
    )


async def process_level_selection(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process level selection.

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

    await state.update_data(level=level)
    await state.set_state(AdminRoiCorridorStates.selecting_mode)
    await message.answer(
        f"**Уровень {level} выбран.**\n\nВыберите режим начисления:",
        parse_mode="Markdown",
        reply_markup=admin_roi_mode_select_keyboard(),
    )


async def process_mode_selection(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process mode selection.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    logger.info(f"[ROI_CORRIDOR] process_mode_selection called, text: {message.text}")

    # Check for navigation
    if await check_cancel_or_back(message, state, session, **data):
        return

    if "Custom" in message.text:
        mode = "custom"
        mode_text = "Custom (случайный из коридора)"
        logger.info("[ROI_CORRIDOR] Selected Custom mode")
    elif "Поровну" in message.text:
        mode = "equal"
        mode_text = "Поровну (фиксированный для всех)"
        logger.info("[ROI_CORRIDOR] Selected Equal mode")
    else:
        logger.warning(f"[ROI_CORRIDOR] Invalid mode selection: {message.text}")
        await message.answer(
            "❌ Неверный режим. Выберите из предложенных вариантов.",
            reply_markup=admin_roi_mode_select_keyboard(),
        )
        return

    await state.update_data(mode=mode, mode_text=mode_text)

    # Immediately ask for values based on mode
    if mode == "custom":
        await state.set_state(AdminRoiCorridorStates.entering_min)
        await message.answer(
            f"**Режим:** {mode_text}\n\n"
            "**Шаг 1/4: Введите минимальный процент коридора**\n\n"
            "Например: `0.8` (для 0.8% в период)\n\n"
            "Это нижняя граница случайного процента.",
            parse_mode="Markdown",
        )
    else:
        await state.set_state(AdminRoiCorridorStates.entering_fixed)
        await message.answer(
            f"**Режим:** {mode_text}\n\n"
            "**Шаг 1/3: Введите фиксированный процент для всех**\n\n"
            "Например: `5.5` (для 5.5% в период)\n\n"
            "Все пользователи будут получать одинаковый процент.",
            parse_mode="Markdown",
        )


async def process_applies_to(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process application scope selection.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    # Check for navigation
    if await check_cancel_or_back(message, state, session, **data):
        return

    if "текущей" in message.text:
        applies_to = "current"
        applies_text = "текущей сессии (ближайшее начисление)"
    elif "следующей" in message.text:
        applies_to = "next"
        applies_text = "следующей сессии (через одно начисление)"
    else:
        await message.answer(
            "❌ Неверный выбор. Выберите из предложенных вариантов.",
            reply_markup=admin_roi_applies_to_keyboard(),
        )
        return

    await state.update_data(applies_to=applies_to, applies_text=applies_text)

    # After selecting when to apply, ask for optional reason/comment
    await state.set_state(AdminRoiCorridorStates.entering_reason)
    await message.answer(
        "📝 **Шаг 3: Введите причину изменения (опционально)**\n\n"
        "Пример: `Экстренное снижение доходности` или `Плановое повышение`\n\n"
        "Если не хотите указывать причину, отправьте `Пропустить`.",
        parse_mode="Markdown",
    )


# Handler registration function
def register_corridor_setup_handlers(router):
    """Register corridor setup handlers to the router."""
    router.message.register(
        start_corridor_setup,
        F.text == "⚙️ Настроить коридоры"
    )
    router.message.register(
        process_level_selection,
        AdminRoiCorridorStates.selecting_level
    )
    router.message.register(
        process_mode_selection,
        AdminRoiCorridorStates.selecting_mode
    )
    router.message.register(
        process_applies_to,
        AdminRoiCorridorStates.selecting_applies_to
    )
