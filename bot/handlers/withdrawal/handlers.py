"""
Main withdrawal handlers module.

This module contains the primary withdrawal menu handlers and entry points
for initiating withdrawal requests.
"""

import logging
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from app.models.user import User
from app.services.user_service import UserService
from app.services.withdrawal_service import WithdrawalService
from bot.i18n.loader import get_text, get_translator, get_user_language
from bot.keyboards.reply import withdrawal_keyboard
from bot.states.withdrawal import WithdrawalStates

from .eligibility import check_withdrawal_eligibility


logger = logging.getLogger(__name__)

# Router will be created in __init__.py and imported there
router = Router()


@router.message(F.text == "💸 Вывести средства")
async def show_withdrawal_menu(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show withdrawal menu."""
    await state.clear()

    session = data.get("session")
    min_amount = "0.20"  # Default fallback

    if session:
        try:
            withdrawal_service = WithdrawalService(session)
            min_val = await withdrawal_service.get_min_withdrawal_amount()
            min_amount = f"{min_val:.2f}"
        except Exception as e:
            logger.error(
                "Failed to fetch minimum withdrawal amount in show_withdrawal_menu: %s",
                e,
                exc_info=True
            )

    text = (
        f"💸 *Вывод средств*\n\n"
        f"ℹ️ Вывод возможен по накоплению *{min_amount} USDT* прибыли.\n"
        f"_Это сделано, чтобы не нагружать выплатную систему, "
        f"а также не переплачивать комиссии за транзакции._\n\n"
        f"Выберите действие:"
    )

    await message.answer(
        text,
        reply_markup=withdrawal_keyboard(),
        parse_mode="Markdown",
    )


@router.message(F.text == "💸 Вывести всю сумму")
async def withdraw_all(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle 'Withdraw All' button."""
    user: User | None = data.get("user")
    if not user:
        await message.answer(get_text('errors.user_not_found'))
        return

    session = data.get("session")
    if not session:
        await message.answer(get_text('errors.system_error'))
        return

    # R13-3: Get user language
    user_language = await get_user_language(session, user.id)

    # Check withdrawal eligibility (finpass for all, phone/email for level 2+)
    can_withdraw, error_msg = await check_withdrawal_eligibility(session, user, user_language)
    if not can_withdraw:
        await message.answer(error_msg, reply_markup=withdrawal_keyboard(), parse_mode="Markdown")
        return

    user_service = UserService(session)
    balance = await user_service.get_user_balance(user.id)
    amount = Decimal(str(balance["available_balance"]))

    # Check minimum
    withdrawal_service = WithdrawalService(session)
    min_amount = await withdrawal_service.get_min_withdrawal_amount()

    if amount < min_amount:
        await message.answer(
            f"❌ Недостаточно средств для вывода!\n\n"
            f"Минимальная сумма: {min_amount} USDT\n"
            f"Ваш баланс: {amount:.2f} USDT",
            reply_markup=withdrawal_keyboard(),
        )
        return

    # Save amount and ask for CONFIRMATION first (convert Decimal to str for JSON)
    await state.update_data(amount=str(amount))
    await state.set_state(WithdrawalStates.waiting_for_confirmation)

    text = (
        f"⚠️ *Подтверждение вывода*\n\n"
        f"💰 Сумма: *{amount:.2f} USDT*\n"
        f"💳 Кошелёк: `{user.wallet_address[:10]}...{user.wallet_address[-6:]}`\n\n"
        f"❗️ Убедитесь, что это ваш *ЛИЧНЫЙ* кошелёк (не биржевой)!\n\n"
        f"Для подтверждения напишите: *да* или *yes*\n"
        f"Для отмены: *нет* или *отмена*"
    )

    await message.answer(text, parse_mode="Markdown")


@router.message(F.text == "💵 Вывести указанную сумму")
async def withdraw_amount(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle 'Withdraw Amount' button."""
    user: User | None = data.get("user")
    if not user:
        await message.answer(get_text('errors.user_not_found'))
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

    withdrawal_service = WithdrawalService(session)
    min_amount = await withdrawal_service.get_min_withdrawal_amount()

    await message.answer(
        f"Введите сумму для вывода (мин. {min_amount} USDT):",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(WithdrawalStates.waiting_for_amount)
