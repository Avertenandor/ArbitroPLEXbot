"""
Deposit level selection handler.

Handles level selection step in deposit creation flow.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.models.user import User
from app.repositories.deposit_level_config_repository import (
    DepositLevelConfigRepository,
)
from bot.keyboards.reply import cancel_keyboard
from bot.messages.error_constants import (
    ERROR_SYSTEM_DOT,
    ERROR_SYSTEM_TRY_START,
    ERROR_USER_NOT_FOUND,
)
from bot.states.deposit import DepositStates, update_deposit_state_data
from bot.utils.formatters import format_balance
from bot.utils.menu_buttons import is_menu_button
from bot.utils.user_context import get_user_from_context

from .utils import extract_level_type_from_button


router = Router()


# Regex pattern for deposit level buttons
# Matches:
# - "🎯 Тестовый ($30-$100)"
# - "💰 Уровень 1 ($100-$500)"
# - "✅ Тестовый ($30-$100) - Активен"
# - "🔒 Уровень 2 ($500-$1000)"
# Note: Only match deposit level buttons, not other buttons
DEPOSIT_LEVEL_PATTERN = (
    r"^(🎯 Тестовый|💰 Уровень 1|💎 Уровень 2|"
    r"🏆 Уровень 3|👑 Уровень 4|🚀 Уровень 5|"
    r"✅ (Тестовый|Уровень \d)|"
    r"🔒 (Тестовый|Уровень \d)).*$"
)


@router.message(F.text.regexp(DEPOSIT_LEVEL_PATTERN))
async def select_deposit_level(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle deposit level selection.

    Flow:
    1. Extract level type from button text
    2. Check if level is available (not active, not locked)
    3. Get level config from database
    4. Show corridor and ask for amount input

    Args:
        message: Telegram message
        state: FSM state
        data: Additional data including session_factory and user
    """
    # Get session for user loading
    session = data.get("session")
    if not session:
        await message.answer(ERROR_SYSTEM_DOT)
        return

    user = await get_user_from_context(message, session, data)
    if not user:
        await message.answer(ERROR_USER_NOT_FOUND)
        return

    # Check if message is a menu button - if so, ignore and let menu handlers process it
    if is_menu_button(message.text or ""):
        return

    # Extract level type from button text
    level_type = extract_level_type_from_button(message.text or "")
    if not level_type:
        await message.answer(
            "❌ Не удалось определить уровень депозита"
        )
        return

    logger.info(
        "User selected deposit level",
        extra={
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "level_type": level_type,
            "button_text": message.text,
        },
    )

    # Check if level is already active (button text contains "Активен")
    is_active_level = "Активен" in (message.text or "")
    if is_active_level:
        active_level_msg = (
            "ℹ️ **Уровень уже активен**\n\n"
            "У вас уже есть активный депозит "
            "этого уровня.\n"
            "Повторная покупка того же уровня "
            "не разрешена.\n\n"
            "Выберите другой уровень депозита "
            "или проверьте свои активные депозиты "
            "в разделе '📦 Мои депозиты'."
        )
        await message.answer(
            active_level_msg,
            parse_mode="Markdown",
        )
        return

    # Check if level is locked (button text contains "🔒")
    is_locked_level = "🔒" in (message.text or "")
    if is_locked_level:
        locked_level_msg = (
            "❌ **Уровень недоступен**\n\n"
            "Этот уровень заблокирован.\n"
            "Проверьте требования для разблокировки "
            "или выберите другой уровень."
        )
        await message.answer(
            locked_level_msg,
            parse_mode="Markdown",
        )
        return

    # Get session factory
    session_factory = data.get("session_factory")
    if not session_factory:
        # Fallback to old session
        session = data.get("session")
        if not session:
            await message.answer(ERROR_SYSTEM_TRY_START)
            return

        config_repo = DepositLevelConfigRepository(session)
        level_config = await config_repo.get_by_level_type(level_type)
    else:
        # NEW pattern: short read transaction
        async with session_factory() as session:
            async with session.begin():
                config_repo = DepositLevelConfigRepository(session)
                level_config = await config_repo.get_by_level_type(level_type)

    if not level_config:
        await message.answer(
            f"❌ Конфигурация уровня '{level_type}' не найдена.\n"
            f"Обратитесь в поддержку."
        )
        return

    # Check if level is active
    if not level_config.is_active:
        inactive_level_msg = (
            f"❌ **Уровень временно недоступен**\n\n"
            f"Уровень '{level_config.name}' временно закрыт "
            f"для новых депозитов.\n"
            f"Выберите другой уровень или попробуйте позже."
        )
        await message.answer(
            inactive_level_msg,
            parse_mode="Markdown",
        )
        return

    # Save level data to state
    await update_deposit_state_data(
        state,
        level_type=level_type,
        level_name=level_config.name,
        min_amount=level_config.min_amount,
        max_amount=level_config.max_amount,
    )

    # Format amounts for display
    min_amt_str = format_balance(level_config.min_amount, decimals=2)
    max_amt_str = format_balance(level_config.max_amount, decimals=2)

    # Show corridor and ask for amount
    text = (
        f"📦 **{level_config.name}**\n\n"
        f"💰 **Коридор сумм депозита:**\n"
        f"От {min_amt_str} до {max_amt_str} USDT\n\n"
        f"💎 **PLEX требование:**\n"
        f"{level_config.plex_per_dollar} PLEX за каждый $1 в сутки\n\n"
        f"📊 **ROI настройки:**\n"
        f"• Ежедневный процент: {level_config.roi_percent}%\n"
        f"• ROI cap: {level_config.roi_cap_percent}%\n\n"
        f"✏️ **Введите сумму депозита в USDT:**\n"
        f"(от {min_amt_str} до {max_amt_str})"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )

    # Set state to entering amount
    await state.set_state(DepositStates.entering_amount)

    logger.info(
        "Level selected, waiting for amount input",
        extra={
            "user_id": user.id,
            "level_type": level_type,
            "min_amount": str(level_config.min_amount),
            "max_amount": str(level_config.max_amount),
        },
    )
