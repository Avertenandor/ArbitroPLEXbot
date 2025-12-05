"""
ROI Corridor level amount management.

Handles the flow for setting deposit level amounts.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deposit_level_version_repository import (
    DepositLevelVersionRepository,
)
from app.services.roi_corridor_service import RoiCorridorService
from app.validators.common import validate_amount
from bot.handlers.admin.roi_corridor.utils import check_cancel_or_back
from bot.keyboards.buttons import NavigationButtons
from bot.keyboards.reply import (
    admin_roi_confirmation_keyboard,
    admin_roi_level_select_keyboard,
    cancel_keyboard,
)
from bot.states.admin import AdminRoiCorridorStates
from bot.utils.admin_utils import clear_state_preserve_admin_token


async def start_amount_setup(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Start level amount setup flow.

    Args:
        message: Message object
        state: FSM context
    """
    await state.set_state(AdminRoiCorridorStates.selecting_level_amount)
    await message.answer(
        "Выберите уровень для настройки суммы:",
        reply_markup=admin_roi_level_select_keyboard(),
    )


async def process_level_amount_selection(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process level selection for amount change.

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

    # Get current amount
    version_repo = DepositLevelVersionRepository(session)
    current_version = await version_repo.get_current_version(level)

    if current_version:
        current_amount = f"{current_version.amount} USDT"
    else:
        current_amount = "Не настроен"

    await state.update_data(level=level, current_amount=current_amount)
    await state.set_state(AdminRoiCorridorStates.setting_level_amount)

    await message.answer(
        f"**Уровень {level} выбран.**\n"
        f"Текущая сумма: **{current_amount}**\n\n"
        "Введите новую сумму в USDT (например: `100`):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def process_amount_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process amount input.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    # Import here to avoid circular dependency
    from bot.handlers.admin.roi_corridor.menu import show_roi_corridor_menu

    if message.text == NavigationButtons.CANCEL:
        await clear_state_preserve_admin_token(state)
        await show_roi_corridor_menu(message, session, **data)
        return

    # Validate amount using common validator
    is_valid, amount, error_msg = validate_amount(
        message.text.strip(),
        min_amount=Decimal("0.01")
    )

    if not is_valid:
        await message.answer(
            f"❌ {error_msg}\n\n"
            "Введите положительное число (например: `100`):",
            parse_mode="Markdown",
        )
        return

    state_data = await state.get_data()
    level = state_data.get("level")
    current_amount = state_data.get("current_amount")

    await state.update_data(new_amount=float(amount))
    await state.set_state(AdminRoiCorridorStates.confirming_level_amount)

    await message.answer(
        f"⚠️ **Подтверждение изменения суммы**\n\n"
        f"**Уровень:** {level}\n"
        f"**Текущая сумма:** {current_amount}\n"
        f"**Новая сумма:** {amount} USDT\n\n"
        "❗️ **ВНИМАНИЕ:**\n"
        "Будет создана новая версия уровня. Старые депозиты продолжат работать "
        "на прежних условиях. Новые депозиты потребуют новую сумму.\n\n"
        "Подтвердить?",
        parse_mode="Markdown",
        reply_markup=admin_roi_confirmation_keyboard(),
    )


async def process_amount_confirmation(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process amount change confirmation.

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
    level = state_data.get("level")
    amount = Decimal(str(state_data.get("new_amount")))
    admin_id = data.get("admin_id")

    if not level or not amount or not admin_id:
        await clear_state_preserve_admin_token(state)
        await message.answer("❌ Ошибка: данные потеряны")
        return

    # Call service to update amount (create new version)
    corridor_service = RoiCorridorService(session)
    success, error = await corridor_service.set_level_amount(
        level=level,
        amount=amount,
        admin_id=admin_id,
    )

    if success:
        await message.answer(
            f"✅ **Сумма успешно обновлена!**\n\n"
            f"**Уровень:** {level}\n"
            f"**Новая сумма:** {amount} USDT\n\n"
            "Изменения вступят в силу для новых депозитов.",
            parse_mode="Markdown",
        )

        # Notify other admins? Maybe later.

    else:
        await message.answer(f"❌ Ошибка: {error}")

    await clear_state_preserve_admin_token(state)
    await show_roi_corridor_menu(message, session, **data)


# Handler registration function
def register_amount_setup_handlers(router):
    """Register amount setup handlers to the router."""
    router.message.register(
        start_amount_setup,
        F.text == "💵 Настроить суммы уровней"
    )
    router.message.register(
        process_level_amount_selection,
        AdminRoiCorridorStates.selecting_level_amount
    )
    router.message.register(
        process_amount_input,
        AdminRoiCorridorStates.setting_level_amount
    )
    router.message.register(
        process_amount_confirmation,
        AdminRoiCorridorStates.confirming_level_amount
    )
