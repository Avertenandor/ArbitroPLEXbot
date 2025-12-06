"""
Deposit transaction hash handler.

Handles transaction hash input and deposit creation.
"""

from decimal import Decimal
from typing import Any

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from app.services.deposit import DepositService
from bot.keyboards.inline import deposit_status_keyboard
from bot.keyboards.reply import cancel_keyboard, main_menu_reply_keyboard
from bot.states.deposit import DepositStates, get_deposit_state_data
from bot.utils.formatters import format_deposit_status
from bot.utils.menu_buttons import is_menu_button

router = Router()


@router.message(DepositStates.waiting_for_tx_hash)
async def process_tx_hash(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process transaction hash for deposit.

    Flow:
    1. Validate transaction hash format
    2. Get deposit parameters from state
    3. Create deposit in database
    4. Show confirmation and status

    Uses session_factory for short transaction during deposit creation.

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

    tx_hash = (message.text or "").strip()

    # Basic validation
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        await message.answer(
            "❌ Неверный формат hash!\n\n"
            "Transaction hash должен начинаться с '0x' "
            "и содержать 66 символов.\n"
            "Попробуйте еще раз:",
            reply_markup=cancel_keyboard(),
        )
        return

    # Get state data
    state_data = await get_deposit_state_data(state)

    logger.info(
        "Processing tx hash",
        extra={
            "user_id": user.id,
            "level_type": state_data.level_type,
            "amount": str(state_data.amount),
            "tx_hash": tx_hash,
        },
    )

    # Map level_type to old level number for compatibility
    # TODO: Refactor DepositService to use level_type instead of level number
    level_mapping = {
        "test": 0,
        "level_1": 1,
        "level_2": 2,
        "level_3": 3,
        "level_4": 4,
        "level_5": 5,
    }
    level_number = level_mapping.get(state_data.level_type, 1)

    session_factory = data.get("session_factory")

    # Validate and create deposit with SHORT transaction
    if not session_factory:
        # Fallback to old session
        session = data.get("session")
        if not session:
            await message.answer("❌ Системная ошибка.")
            await state.clear()
            return

        # Note: Validation is skipped here as we already validated in level selection
        # and amount input steps
        deposit_service = DepositService(session)
        redis_client = data.get("redis_client")
        try:
            deposit = await deposit_service.create_deposit(
                user_id=user.id,
                level=level_number,
                amount=state_data.amount,
                tx_hash=tx_hash,
                redis_client=redis_client,
            )
        except ValueError as exc:
            # R17-3: Show controlled business errors (including emergency stop)
            await message.answer(str(exc))
            await state.clear()
            return
    else:
        # NEW pattern: short transaction for creation
        async with session_factory() as session:
            async with session.begin():
                deposit_service = DepositService(session)
                redis_client = data.get("redis_client")
                try:
                    deposit = await deposit_service.create_deposit(
                        user_id=user.id,
                        level=level_number,
                        amount=state_data.amount,
                        tx_hash=tx_hash,
                        redis_client=redis_client,
                    )
                except ValueError as exc:
                    # R17-3: Show controlled business errors (including emergency stop)
                    await message.answer(str(exc))
                    await state.clear()
                    return
        # Transaction closed here

    logger.info(
        "Deposit created with tx hash",
        extra={
            "deposit_id": deposit.id,
            "user_id": user.id,
            "level_type": state_data.level_type,
            "level_number": level_number,
            "amount": str(state_data.amount),
            "tx_hash": tx_hash,
        },
    )

    # Get system wallet address
    from app.config.settings import settings

    system_wallet = settings.system_wallet_address

    # Show deposit created confirmation
    confirmation_text = (
        f"✅ **Депозит создан!**\n\n"
        f"📦 Уровень: {state_data.level_name}\n"
        f"💰 Сумма: {state_data.amount} USDT\n"
        f"💎 Ежедневный PLEX: {state_data.plex_daily} PLEX\n"
        f"🆔 ID депозита: {deposit.id}\n"
        f"🔗 Hash транзакции: `{tx_hash}`\n\n"
    )

    # Check ROI cap for level 1
    if level_number == 1:
        roi_cap = state_data.amount * Decimal("5.0")
        confirmation_text += f"💰 ROI Cap: {roi_cap} USDT (максимум можно заработать)\n\n"

    confirmation_text += (
        f"📊 **Проверить транзакцию:**\n"
        f"https://bscscan.com/tx/{tx_hash}\n\n"
        f"⏱ Депозит будет автоматически активирован "
        f"после подтверждения транзакции (обычно 2-5 минут)."
    )

    is_admin = data.get("is_admin", False)

    # Get blacklist entry with proper session handling
    blacklist_entry = None
    if user and session_factory:
        async with session_factory() as fresh_session:
            blacklist_repo = BlacklistRepository(fresh_session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                user.telegram_id
            )
    elif user and data.get("session"):
        blacklist_repo = BlacklistRepository(data.get("session"))
        blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)

    await message.answer(
        confirmation_text,
        parse_mode="Markdown",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )

    # Get deposit status with confirmations
    deposit_service_for_status = None
    if session_factory:
        async with session_factory() as fresh_session:
            async with fresh_session.begin():
                deposit_service_for_status = DepositService(fresh_session)
                status_info = await deposit_service_for_status.get_deposit_status_with_confirmations(
                    deposit.id
                )
    else:
        session = data.get("session")
        if session:
            deposit_service_for_status = DepositService(session)
            status_info = await deposit_service_for_status.get_deposit_status_with_confirmations(
                deposit.id
            )

    # Show deposit status with progress bar
    if status_info and status_info.get("success"):
        confirmations = status_info.get("confirmations", 0)
        estimated_time = status_info.get("estimated_time", "2-5 минут")

        status_text = format_deposit_status(
            amount=state_data.amount,
            level=level_number,
            confirmations=confirmations,
            required_confirmations=12,
            estimated_time=estimated_time,
        )

        await message.answer(
            status_text,
            parse_mode="Markdown",
            reply_markup=deposit_status_keyboard(deposit.id),
        )

    await state.clear()
