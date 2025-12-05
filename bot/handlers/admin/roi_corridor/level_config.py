"""
ROI Corridor level configuration display.

Shows ROI configuration for specific levels and current settings.
"""

from __future__ import annotations

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.roi_corridor_service import RoiCorridorService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import (
    admin_roi_corridor_menu_keyboard,
    admin_roi_mode_select_keyboard,
)
from bot.states.admin import AdminRoiCorridorStates


async def show_level_roi_config(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    level: int,
    from_level_management: bool = False,
    **data: Any,
) -> None:
    """
    Show ROI configuration for specific level and start setup.

    This function is called from deposit_management when admin clicks
    "💰 Настроить коридор доходности" button.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        level: Deposit level number (1-5)
        from_level_management: Whether called from level management screen
        data: Handler data
    """
    logger.info(f"[ROI_CORRIDOR] show_level_roi_config called for level {level}")

    # Verify admin access
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Get current ROI settings for this level
    logger.info(f"[ROI_CORRIDOR] Getting settings for level {level}")
    roi_service = RoiCorridorService(session)
    settings = await roi_service.get_corridor_config(level)
    accrual_period = await roi_service.get_accrual_period_hours()

    logger.info(f"[ROI_CORRIDOR] Settings: {settings}, period: {accrual_period}")

    mode = settings["mode"]
    mode_text = "Custom (случайный из коридора)" if mode == "custom" else "Поровну (фиксированный)"

    if mode == "custom":
        corridor_text = f"{settings['roi_min']}% - {settings['roi_max']}%"
    else:
        corridor_text = f"{settings['roi_fixed']}% (фиксированный)"

    text = f"""
💰 **Настройка коридора доходности для Уровня {level}**

📊 **Текущие настройки:**
• Режим: {mode_text}
• Коридор: {corridor_text}
• Период начисления: каждые {accrual_period} часов

**Что вы хотите сделать?**
    """.strip()

    # Save level to state and start configuration
    await state.update_data(level=level, from_level_management=from_level_management)
    await state.set_state(AdminRoiCorridorStates.selecting_mode)

    logger.info(f"[ROI_CORRIDOR] Sending mode selection keyboard for level {level}")

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_roi_mode_select_keyboard(),
    )

    logger.info("[ROI_CORRIDOR] Mode selection message sent successfully")


async def show_current_settings(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show current corridor settings for all levels.

    Args:
        message: Message object
        session: Database session
        data: Handler data
    """
    # Verify admin access
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    corridor_service = RoiCorridorService(session)

    text = "📊 **Текущие настройки коридоров:**\n\n"

    for level in range(1, 6):
        config = await corridor_service.get_corridor_config(level)
        mode_text = (
            "Custom" if config["mode"] == "custom" else "Поровну"
        )

        text += f"**{level}️⃣ Уровень {level}:** {mode_text}\n"

        if config["mode"] == "custom":
            text += f"   Коридор: {config['roi_min']}% - {config['roi_max']}%\n"
        else:
            text += f"   Фиксированный: {config['roi_fixed']}%\n"

        text += "\n"

    period = await corridor_service.get_accrual_period_hours()
    text += f"⏱ **Период начисления:** {period} часов"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_roi_corridor_menu_keyboard(),
    )


# Handler registration function
def register_level_config_handlers(router):
    """Register level config handlers to the router."""
    router.message.register(
        show_current_settings,
        F.text == "📊 Текущие настройки"
    )
