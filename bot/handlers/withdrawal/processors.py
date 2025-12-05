"""
Withdrawal processing module.

This module handles the processing of withdrawal amounts, confirmations,
and financial password verification.
"""

import asyncio
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from app.models.user import User
from app.services.user_service import UserService
from app.services.withdrawal_service import WithdrawalService
from app.validators.common import validate_amount
from bot.i18n.loader import get_text, get_translator, get_user_language
from bot.keyboards.reply import (
    finpass_input_keyboard,
    main_menu_reply_keyboard,
    withdrawal_keyboard,
)
from bot.states.withdrawal import WithdrawalStates
from bot.utils.menu_buttons import is_menu_button

from .auto_payout import _safe_process_auto_payout
from .eligibility import check_withdrawal_eligibility

# Router will be created in __init__.py and imported there
router = Router()


@router.message(WithdrawalStates.waiting_for_confirmation)
async def confirm_withdrawal(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle withdrawal confirmation."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return

    # Check for menu button
    if is_menu_button(message.text or ""):
        await state.clear()
        return

    answer = (message.text or "").strip().lower()

    if answer in ("да", "yes", "д", "y"):
        # Confirmed - ask for password
        state_data = await state.get_data()
        amount = state_data.get("amount")

        text = (
            f"💸 *Вывод средств*\n\n"
            f"Сумма к выводу: *{amount} USDT*\n\n"
            f"🔐 Введите ваш финансовый пароль:"
        )

        await message.answer(text, reply_markup=finpass_input_keyboard(), parse_mode="Markdown")
        await state.set_state(WithdrawalStates.waiting_for_financial_password)

    elif answer in ("нет", "no", "н", "n", "отмена", "cancel"):
        await state.clear()
        await message.answer(
            "❌ Вывод отменён.",
            reply_markup=withdrawal_keyboard(),
        )

    else:
        await message.answer(
            "⚠️ Напишите *да* для подтверждения или *нет* для отмены.",
            parse_mode="Markdown",
        )


@router.message(WithdrawalStates.waiting_for_amount)
async def process_withdrawal_amount(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process withdrawal amount."""
    user: User | None = data.get("user")
    if not user:
        await message.answer(get_text('errors.user_not_found'))
        await state.clear()
        return

    session = data.get("session")
    if not session:
        await message.answer(get_text('errors.system_error'))
        await state.clear()
        return

    # R13-3: Get user language
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    # Check withdrawal eligibility (finpass for all, phone/email for level 2+)
    can_withdraw, error_msg = await check_withdrawal_eligibility(session, user, user_language)
    if not can_withdraw:
        await message.answer(error_msg, reply_markup=withdrawal_keyboard(), parse_mode="Markdown")
        await state.clear()
        return

    if is_menu_button(message.text or ""):
        await state.clear()
        return

    # Validate amount using common validator
    is_valid, amount, error_msg = validate_amount(
        (message.text or "").strip(),
        min_amount=Decimal("0")
    )

    if not is_valid:
        await message.answer(
            f"❌ Неверный формат суммы!\n\n{error_msg}"
        )
        return

    withdrawal_service = WithdrawalService(session)
    min_amount = await withdrawal_service.get_min_withdrawal_amount()

    if amount < min_amount:
        await message.answer(
            f"❌ Сумма слишком маленькая!\n\n"
            f"Минимальная сумма: {min_amount} USDT\n"
            f"Попробуйте еще раз:"
        )
        return

    session_factory = data.get("session_factory")

    if not session_factory:
        user_service = UserService(session)
        balance = await user_service.get_user_balance(user.id)
    else:
        async with session_factory() as temp_session:
            async with temp_session.begin():
                user_service = UserService(temp_session)
                balance = await user_service.get_user_balance(user.id)

    if not balance or Decimal(str(balance["available_balance"])) < amount:
        await message.answer(
            f"❌ Недостаточно средств!\n\n"
            f"Доступно: {balance['available_balance']:.2f} USDT\n"
            f"Попробуйте меньшую сумму:"
        )
        return

    # Convert Decimal to str for JSON serialization in FSM state
    await state.update_data(amount=str(amount))

    text = (
        f"💸 *Вывод средств*\n\n"
        f"Сумма: *{amount} USDT*\n\n"
        f"🔐 Введите ваш финансовый пароль:"
    )

    await message.answer(text, reply_markup=finpass_input_keyboard(), parse_mode="Markdown")
    await state.set_state(WithdrawalStates.waiting_for_financial_password)


@router.message(WithdrawalStates.waiting_for_financial_password)
async def process_financial_password(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process financial password and create withdrawal."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return

    # Handle cancel button
    if (message.text or "").strip() == "❌ Отменить вывод":
        await state.clear()
        await message.answer(
            "❌ Вывод отменён.",
            reply_markup=withdrawal_keyboard(),
        )
        return

    if is_menu_button(message.text or ""):
        await state.clear()
        return

    # Check rate limit
    telegram_id = message.from_user.id if message.from_user else None
    if telegram_id:
        from bot.utils.operation_rate_limit import OperationRateLimiter
        redis_client = data.get("redis_client")
        rate_limiter = OperationRateLimiter(redis_client=redis_client)
        allowed, error_msg = await rate_limiter.check_withdrawal_limit(telegram_id)
        if not allowed:
            await message.answer(
                error_msg or "Слишком много заявок на вывод",
                reply_markup=withdrawal_keyboard(),
            )
            await state.clear()
            return

    password = (message.text or "").strip()

    try:
        await message.delete()
    except Exception as e:
        logger.debug(f"Failed to delete password message: {e}")

    session_factory = data.get("session_factory")

    # Verify password and create withdrawal
    if not session_factory:
        await message.answer("❌ Системная ошибка (no session factory)")
        return

    try:
        transaction = None
        error = None
        is_auto = False
        no_finpass = False

        async with session_factory() as session:
            user_service = UserService(session)
            # Re-check user (detached)
            current_user = await user_service.get_by_id(user.id)
            if not current_user:
                raise ValueError("User not found")

            # Check password
            if not current_user.financial_password:
                no_finpass = True
            else:
                # Verify password with rate limiting
                is_valid, rate_error = await user_service.verify_financial_password(
                    current_user.id, password
                )
                if not is_valid:
                    error = rate_error or "Неверный финансовый пароль"
                else:
                    # Proceed
                    state_data = await state.get_data()
                    amount = Decimal(str(state_data.get("amount")))

                    balance = await user_service.get_user_balance(current_user.id)

                    withdrawal_service = WithdrawalService(session)
                    transaction, error, is_auto = await withdrawal_service.request_withdrawal(
                        user_id=current_user.id,
                        amount=amount,
                        available_balance=Decimal(str(balance["available_balance"])),
                    )

        # Outside session - send messages
        if no_finpass:
            await message.answer(
                "❌ Финансовый пароль не установлен!",
                reply_markup=main_menu_reply_keyboard(user=user)
            )
        elif error:
            await message.answer(
                f"❌ {error}",
                reply_markup=withdrawal_keyboard(),
            )
        elif transaction:
            net_amount = transaction.amount - transaction.fee
            if is_auto:
                await message.answer(
                    f"✅ *Заявка #{transaction.id} принята!*\n\n"
                    f"💰 Запрошено: *{transaction.amount} USDT*\n"
                    f"💸 Комиссия: *{transaction.fee} USDT*\n"
                    f"✨ К получению: *{net_amount} USDT*\n"
                    f"💳 Кошелек: `{transaction.to_address[:10]}...{transaction.to_address[-6:]}`\n\n"
                    f"⚡️ *Автоматическая выплата одобрена*\n"
                    f"Средства поступят в течение 1-5 минут.\n\n"
                    f"📊 Статус: '📜 История выводов'",
                    parse_mode="Markdown",
                    reply_markup=main_menu_reply_keyboard(user=user)
                )
                # Trigger background task with error handling
                # CRITICAL: Send net_amount (amount - fee) to user, not gross amount
                asyncio.create_task(
                    _safe_process_auto_payout(
                        transaction.id,
                        net_amount,
                        transaction.to_address,
                        message.bot,
                        user.telegram_id
                    )
                )
            else:
                await message.answer(
                    f"✅ *Заявка #{transaction.id} создана!*\n\n"
                    f"💰 Запрошено: *{transaction.amount} USDT*\n"
                    f"💸 Комиссия: *{transaction.fee} USDT*\n"
                    f"✨ К получению: *{net_amount} USDT*\n"
                    f"💳 Кошелек: `{transaction.to_address[:10]}...{transaction.to_address[-6:]}`\n\n"
                    f"⏱ *Время обработки:* до 24 часов\n"
                    f"📊 Статус можно проверить в '📜 История выводов'",
                    parse_mode="Markdown",
                    reply_markup=main_menu_reply_keyboard(user=user)
                )
        else:
            await message.answer(
                "❌ Неизвестная ошибка",
                reply_markup=withdrawal_keyboard(),
            )

    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке заявки",
            reply_markup=withdrawal_keyboard(),
        )

    await state.clear()


@router.message(F.text.regexp(r"^\d+([.,]\d+)?$"))
async def handle_smart_withdrawal_amount(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Smart handler for numeric input in withdrawal menu context.
    Allows users to type amount directly without clicking button first.
    """
    # Check if user is in withdrawal menu context
    state_data = await state.get_data()
    if not state_data.get("in_withdrawal_menu"):
        # Not in withdrawal context, let other handlers process
        return

    user: User | None = data.get("user")
    if not user:
        return

    session = data.get("session")
    if not session:
        await message.answer(get_text('errors.system_error'))
        return

    # R13-3: Get user language
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    # Check withdrawal eligibility (finpass for all, phone/email for level 2+)
    can_withdraw, error_msg = await check_withdrawal_eligibility(session, user, user_language)
    if not can_withdraw:
        await message.answer(error_msg, reply_markup=withdrawal_keyboard(), parse_mode="Markdown")
        return

    # Validate amount using common validator
    is_valid, amount, error_msg = validate_amount(
        (message.text or "").strip(),
        min_amount=Decimal("0.01")  # Must be greater than 0
    )

    if not is_valid:
        await message.answer(
            f"❌ Неверный формат суммы!\n\n{error_msg}",
            reply_markup=withdrawal_keyboard(),
        )
        return

    # Check minimum withdrawal amount
    withdrawal_service = WithdrawalService(session)
    min_amount = await withdrawal_service.get_min_withdrawal_amount()

    if amount < min_amount:
        await message.answer(
            f"❌ Минимальная сумма вывода: {min_amount} USDT",
            reply_markup=withdrawal_keyboard(),
        )
        return

    # Check balance
    user_service = UserService(session)
    balance = await user_service.get_user_balance(user.id)
    available = Decimal(str(balance["available_balance"]))

    if amount > available:
        await message.answer(
            f"❌ Недостаточно средств!\n\n"
            f"Доступно: {available:.2f} USDT\n"
            f"Запрошено: {amount:.2f} USDT",
            reply_markup=withdrawal_keyboard(),
        )
        return

    # Clear withdrawal menu context and proceed to password confirmation
    await state.update_data(
        in_withdrawal_menu=False,
        amount=str(amount),
    )
    await state.set_state(WithdrawalStates.waiting_for_financial_password)

    await message.answer(
        f"💸 *Вывод средств*\n\n"
        f"Сумма: *{amount:.2f} USDT*\n\n"
        f"🔐 Введите ваш финансовый пароль:",
        parse_mode="Markdown",
        reply_markup=finpass_input_keyboard(),
    )
