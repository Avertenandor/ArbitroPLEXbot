"""
Admin Withdrawals - Details View Handler.

Handles withdrawal selection and displaying detailed withdrawal information.
"""

import re
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus
from app.services.user_service import UserService
from app.services.withdrawal_service import WithdrawalService
from bot.keyboards.reply import (
    admin_withdrawal_detail_keyboard,
    admin_withdrawals_keyboard,
)
from bot.states.admin_states import AdminStates
from bot.utils.admin_utils import clear_state_preserve_admin_token
from bot.utils.formatters import format_usdt


router = Router(name="admin_withdrawals_details")


@router.message(
    F.text.regexp(r"^💸 #(\d+) \|"),
    AdminStates.selecting_withdrawal,
)
async def handle_withdrawal_selection(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Process withdrawal selection from button and show details."""
    text = message.text or ""

    # Extract withdrawal ID from button text: "💸 #123 | 100.00 | @user"
    match = re.match(r"^💸 #(\d+) \|", text, re.UNICODE)
    if not match:
        await message.answer(
            "❌ Не удалось определить заявку. Попробуйте снова.",
            reply_markup=admin_withdrawals_keyboard(),
        )
        await clear_state_preserve_admin_token(state)
        return

    withdrawal_id = int(match.group(1))

    # Get withdrawal details
    withdrawal_service = WithdrawalService(session)
    withdrawal = await withdrawal_service.get_withdrawal_by_id(withdrawal_id)

    if not withdrawal:
        await message.answer(
            f"❌ Заявка #{withdrawal_id} не найдена.",
            reply_markup=admin_withdrawals_keyboard(),
        )
        await clear_state_preserve_admin_token(state)
        return

    if withdrawal.status != TransactionStatus.PENDING.value:
        status_text = {
            TransactionStatus.CONFIRMED.value: "уже одобрена",
            TransactionStatus.FAILED.value: "уже отклонена",
        }.get(withdrawal.status, f"в статусе {withdrawal.status}")

        await message.answer(
            f"❌ Заявка #{withdrawal_id} {status_text}.",
            reply_markup=admin_withdrawals_keyboard(),
        )
        await clear_state_preserve_admin_token(state)
        return

    await state.update_data(withdrawal_id=withdrawal_id)
    await state.set_state(AdminStates.viewing_withdrawal)

    # Get user info and stats
    user_service = UserService(session)
    user = await user_service.find_by_id(withdrawal.user_id)
    username = f"@{user.username}" if user and user.username else f"ID: {withdrawal.user_id}"

    user_balance = await user_service.get_user_balance(withdrawal.user_id)
    history_text = ""
    if user_balance:
        total_dep = user_balance.get('total_deposits', 0)
        total_wd = user_balance.get('total_withdrawals', 0)
        history_text = f"📊 История: депозиты {format_usdt(total_dep)}, выводы {format_usdt(total_wd)}\n"

    date = withdrawal.created_at.strftime("%d.%m.%Y %H:%M")
    net_amount = withdrawal.amount - withdrawal.fee

    text = (
        f"💸 **Заявка на вывод #{withdrawal.id}**\n\n"
        f"👤 Пользователь: {username}\n"
        f"{history_text}"
        f"💰 Запрошено: `{format_usdt(withdrawal.amount)} USDT`\n"
        f"💸 Комиссия: `{format_usdt(withdrawal.fee)} USDT`\n"
        f"✨ К отправке: `{format_usdt(net_amount)} USDT`\n"
        f"💳 Кошелек: `{withdrawal.to_address}`\n"
        f"📅 Дата: {date}\n\n"
        "Выберите действие:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_withdrawal_detail_keyboard(),
    )


@router.message(AdminStates.viewing_withdrawal, F.text == "✅ Одобрить")
async def handle_approve_request(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle approval request from detail view."""
    await state.update_data(withdrawal_action="approve")
    # Import here to avoid circular dependency
    from bot.handlers.admin.withdrawals.approval import _show_confirmation

    await _show_confirmation(message, state, session, "approve")


@router.message(AdminStates.viewing_withdrawal, F.text == "❌ Отклонить")
async def handle_reject_request(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle rejection request from detail view."""
    await state.update_data(withdrawal_action="reject")
    # Import here to avoid circular dependency
    from bot.handlers.admin.withdrawals.approval import _show_confirmation

    await _show_confirmation(message, state, session, "reject")
