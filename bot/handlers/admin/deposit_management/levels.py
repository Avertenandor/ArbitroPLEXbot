"""
Deposit Level Management Display Handler

Provides deposit level management interface:
- Display all levels with current status
- Show individual level details and actions
- Level enable/disable interface
- ROI configuration access
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deposit_level_version_repository import (
    DepositLevelVersionRepository,
)
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import (
    admin_deposit_level_actions_keyboard,
    admin_deposit_levels_keyboard,
)
from bot.states.admin import AdminDepositManagementStates
from bot.utils.formatters import format_usdt

router = Router(name="admin_deposit_management_levels")


@router.message(F.text == "⚙️ Управление уровнями")
async def show_levels_management(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show level management menu with current status.

    Args:
        message: Message object
        session: Database session
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    global_settings_repo = GlobalSettingsRepository(session)
    settings = await global_settings_repo.get_settings()
    version_repo = DepositLevelVersionRepository(session)

    max_level = settings.max_open_deposit_level

    text = "⚙️ **Управление уровнями депозитов**\n\n"
    text += f"Максимальный открытый уровень: **{max_level}**\n\n"
    text += "**Статус уровней:**\n\n"

    for level_num in range(1, 6):
        current_version = await version_repo.get_current_version(level_num)

        if current_version:
            status = "✅ Активен" if current_version.is_active else "❌ Отключен"
            amount = format_usdt(current_version.amount)
        else:
            status = "⚠️ Не настроен"
            amount = "N/A"

        emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][level_num - 1]
        text += f"{emoji} **Уровень {level_num}** ({amount}): {status}\n"

    text += "\n💡 Выберите уровень для управления:"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_levels_keyboard(),
    )


async def show_level_actions_for_level(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    level: int,
    **data: Any,
) -> None:
    """
    Show actions for specific level (helper).

    Args:
        message: Message object
        session: Database session
        state: FSM context
        level: Level number
        data: Handler data
    """
    # Get level status
    version_repo = DepositLevelVersionRepository(session)
    current_version = await version_repo.get_current_version(level)

    if not current_version:
        await message.answer(
            f"⚠️ Уровень {level} не настроен в системе.",
            reply_markup=admin_deposit_levels_keyboard(),
        )
        return

    is_active = current_version.is_active

    # Save level to state
    await state.update_data(managing_level=level)
    await state.set_state(AdminDepositManagementStates.managing_level)

    status_text = "✅ Активен" if is_active else "❌ Отключен"

    text = f"""
⚙️ **Управление уровнем {level}**

Сумма: {format_usdt(current_version.amount)}
Статус: {status_text}
ROI: {current_version.roi_percent}%
ROI Cap: {current_version.roi_cap_percent}%

Выберите действие:
    """.strip()

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_level_actions_keyboard(level, is_active),
    )


@router.message(F.text.startswith("Уровень "))
async def show_level_actions(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show actions for specific level.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Extract level number
    try:
        level = int(message.text.split()[1])
        if level < 1 or level > 5:
            raise ValueError
    except (ValueError, IndexError):
        await message.answer(
            "❌ Неверный формат уровня.",
            reply_markup=admin_deposit_levels_keyboard(),
        )
        return

    await show_level_actions_for_level(message, session, state, level, **data)
