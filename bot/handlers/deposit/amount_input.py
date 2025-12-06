"""
Deposit amount input handler.

Handles amount input step in deposit creation flow.
"""

from typing import Any

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.models.user import User
from app.repositories.deposit_level_config_repository import DepositLevelConfigRepository
from bot.keyboards.reply import cancel_keyboard, main_menu_reply_keyboard
from bot.states.deposit import DepositStates, get_deposit_state_data, update_deposit_state_data
from bot.utils.menu_buttons import is_menu_button

from .utils import format_amount, validate_amount_input

router = Router()


@router.message(DepositStates.entering_amount)
async def process_deposit_amount(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process deposit amount input.

    Flow:
    1. Validate amount format
    2. Get level config from state
    3. Check if amount is in corridor
    4. Calculate daily PLEX requirement
    5. Show payment details (USDT wallet address)
    6. Ask for transaction hash

    Args:
        message: Telegram message
        state: FSM state
        data: Additional data including session_factory and user
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return

    # Check if message is a menu button or cancel - if so, clear state and ignore
    if is_menu_button(message.text or "") or message.text == "❌ Отмена":
        await state.clear()
        if message.text == "❌ Отмена":
            await message.answer(
                "Создание депозита отменено.",
                reply_markup=main_menu_reply_keyboard(user=user),
            )
        return  # Let menu handlers process this

    # Validate amount input
    is_valid, amount, error_msg = validate_amount_input(message.text or "")
    if not is_valid or amount is None:
        await message.answer(
            f"❌ **Неверная сумма**\n\n{error_msg}\n\nПопробуйте еще раз:",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        return

    # Get state data
    state_data = await get_deposit_state_data(state)

    logger.info(
        "Processing amount input",
        extra={
            "user_id": user.id,
            "level_type": state_data.level_type,
            "amount": str(amount),
            "min_amount": str(state_data.min_amount),
            "max_amount": str(state_data.max_amount),
        },
    )

    # Check if amount is in corridor
    if amount < state_data.min_amount or amount > state_data.max_amount:
        min_str = format_amount(state_data.min_amount)
        max_str = format_amount(state_data.max_amount)
        await message.answer(
            f"❌ **Сумма вне коридора**\n\n"
            f"Сумма {format_amount(amount)} USDT не входит в допустимый коридор.\n\n"
            f"Для уровня '{state_data.level_name}' допустимы суммы:\n"
            f"**от {min_str} до {max_str} USDT**\n\n"
            f"Введите корректную сумму:",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        return

    # Get level config to calculate PLEX requirement
    session_factory = data.get("session_factory")
    if not session_factory:
        # Fallback to old session
        session = data.get("session")
        if not session:
            await message.answer("❌ Системная ошибка.")
            await state.clear()
            return

        config_repo = DepositLevelConfigRepository(session)
        level_config = await config_repo.get_by_level_type(state_data.level_type)
    else:
        # NEW pattern: short read transaction
        async with session_factory() as session:
            async with session.begin():
                config_repo = DepositLevelConfigRepository(session)
                level_config = await config_repo.get_by_level_type(state_data.level_type)

    if not level_config:
        await message.answer("❌ Ошибка получения конфигурации уровня")
        await state.clear()
        return

    # Calculate daily PLEX requirement
    plex_daily = level_config.calculate_daily_plex(amount)

    # Save amount and plex_daily to state
    await update_deposit_state_data(
        state,
        amount=amount,
        plex_daily=plex_daily,
    )

    # Get system wallet address
    from app.config.settings import settings

    system_wallet = settings.system_wallet_address

    # Show payment details
    text = (
        f"✅ **Параметры депозита подтверждены**\n\n"
        f"📦 Уровень: {state_data.level_name}\n"
        f"💰 Сумма: {format_amount(amount)} USDT\n"
        f"💎 Ежедневный PLEX: {format_amount(plex_daily)} PLEX\n\n"
        f"📝 **Следующий шаг:**\n"
        f"Отправьте **ровно {format_amount(amount)} USDT** на адрес:\n\n"
        f"`{system_wallet}`\n\n"
        f"⚠️ **ВАЖНО:**\n"
        f"• Сеть: **BSC (BEP-20)**\n"
        f"• Используйте личный кошелек (MetaMask, Trust Wallet, SafePal, Ledger)\n"
        f"• 🚫 Не используйте внутренние переводы бирж (Internal Transfer)\n"
        f"• 💡 Комиссия сети уже включена в сумму депозита\n\n"
        f"После отправки введите hash транзакции:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )

    # Set state to waiting for tx hash
    await state.set_state(DepositStates.waiting_for_tx_hash)

    logger.info(
        "Amount accepted, waiting for tx hash",
        extra={
            "user_id": user.id,
            "level_type": state_data.level_type,
            "amount": str(amount),
            "plex_daily": str(plex_daily),
        },
    )
