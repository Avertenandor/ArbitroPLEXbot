"""
Deposit Management Search Handler

Provides user deposit search functionality:
- Start deposit search flow
- Process user ID input
- Display user deposits with details
- Show deposit status and ROI progress
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus
from app.repositories.deposit_repository import DepositRepository
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_deposit_management_keyboard, cancel_keyboard
from bot.states.admin import AdminDepositManagementStates
from bot.utils.admin_utils import clear_state_preserve_admin_token
from bot.utils.formatters import format_usdt
from bot.utils.user_loader import UserLoader


router = Router(name="admin_deposit_management_search")


@router.message(F.text == "🔍 Найти депозиты пользователя")
async def start_search_user_deposits(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Start user deposit search flow.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(AdminDepositManagementStates.searching_user_deposits)

    await message.answer(
        "🔍 **Поиск депозитов пользователя**\n\n"
        "Введите Telegram ID пользователя:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(AdminDepositManagementStates.searching_user_deposits)
async def process_user_id_for_deposits(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process user ID and show their deposits.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Check for cancel
    if message.text == "❌ Отмена":
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Поиск отменён.",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Check if menu button
    from bot.utils.menu_buttons import is_menu_button

    if message.text and is_menu_button(message.text):
        await clear_state_preserve_admin_token(state)
        return

    # Parse Telegram ID
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Неверный формат! Введите числовой Telegram ID.",
            reply_markup=cancel_keyboard(),
        )
        return

    # Find user using UserLoader
    user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    if not user:
        await message.answer(
            f"❌ Пользователь с ID `{telegram_id}` не найден.",
            parse_mode="Markdown",
            reply_markup=admin_deposit_management_keyboard(),
        )
        await clear_state_preserve_admin_token(state)
        return

    # Get user's deposits
    deposit_repo = DepositRepository(session)
    deposits = await deposit_repo.find_by(user_id=user.id)

    if not deposits:
        await message.answer(
            f"ℹ️ У пользователя `{telegram_id}` нет депозитов.",
            parse_mode="Markdown",
            reply_markup=admin_deposit_management_keyboard(),
        )
        await clear_state_preserve_admin_token(state)
        return

    # Format deposits
    text = f"📋 **Депозиты пользователя {telegram_id}**\n"
    text += f"Username: @{user.username or 'N/A'}\n\n"

    for deposit in deposits:
        status_emoji = {
            TransactionStatus.PENDING.value: "⏳",
            TransactionStatus.CONFIRMED.value: "✅",
            TransactionStatus.FAILED.value: "❌",
        }.get(deposit.status, "❓")

        roi_progress = ""
        if deposit.status == TransactionStatus.CONFIRMED.value:
            if deposit.is_roi_completed:
                roi_progress = " (ROI завершён)"
            else:
                percent = (
                    (deposit.roi_paid_amount / deposit.roi_cap_amount * 100)
                    if deposit.roi_cap_amount > 0
                    else 0
                )
                roi_progress = f" (ROI: {percent:.1f}%)"

        text += (
            f"{status_emoji} **Уровень {deposit.level}** - {format_usdt(deposit.amount)}\n"
            f"   ID: `{deposit.id}`\n"
            f"   Статус: {deposit.status}{roi_progress}\n"
            f"   Заработано: {format_usdt(deposit.roi_paid_amount)} USDT\n"
            f"   Дата: {deposit.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_management_keyboard(),
    )
    await clear_state_preserve_admin_token(state)
