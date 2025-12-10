"""
Admin Withdrawals - History Handler.

Handles viewing approved and rejected withdrawal history.
"""

from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.services.withdrawal_service import WithdrawalService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_withdrawals_keyboard
from bot.utils.formatters import format_usdt


router = Router(name="admin_withdrawals_history")


@router.message(F.text == "📋 Одобренные выводы")
async def handle_approved_withdrawals(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show approved withdrawals"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    WithdrawalService(session)

    try:
        # Get approved withdrawals (last 10)
        stmt = (
            select(Transaction)
            .where(
                Transaction.type == TransactionType.WITHDRAWAL.value,
                Transaction.status == TransactionStatus.CONFIRMED.value,
            )
            .order_by(desc(Transaction.created_at))
            .limit(10)
        )
        result = await session.execute(stmt)
        approved_withdrawals = result.scalars().all()

        text = "✅ **Одобренные заявки на вывод**\n\n"

        if not approved_withdrawals:
            text += "Нет одобренных заявок."
        else:
            for idx, withdrawal in enumerate(approved_withdrawals, 1):
                date = withdrawal.created_at.strftime("%d.%m.%Y %H:%M")
                text += f"**{idx}. Заявка #{withdrawal.id}**\n"
                text += f"💰 Сумма: {format_usdt(withdrawal.amount)} USDT\n"
                text += f"👤 Пользователь ID: {withdrawal.user_id}\n"
                text += f"💳 Кошелек: `{withdrawal.to_address}`\n"
                if withdrawal.tx_hash:
                    text += f"🔗 TX: `{withdrawal.tx_hash}`\n"
                text += f"📅 Дата: {date}\n\n"

        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=admin_withdrawals_keyboard(),
        )

    except Exception as e:
        await session.rollback()
        await message.answer(
            f"❌ Ошибка при загрузке заявок: {str(e)}",
            reply_markup=admin_withdrawals_keyboard(),
        )


@router.message(F.text == "🚫 Отклоненные выводы")
async def handle_rejected_withdrawals(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show rejected withdrawals"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    WithdrawalService(session)

    try:
        # Get rejected withdrawals (last 10)
        stmt = (
            select(Transaction)
            .where(
                Transaction.type == TransactionType.WITHDRAWAL.value,
                Transaction.status == TransactionStatus.FAILED.value,
            )
            .order_by(desc(Transaction.created_at))
            .limit(10)
        )
        result = await session.execute(stmt)
        rejected_withdrawals = result.scalars().all()

        text = "❌ **Отклоненные заявки на вывод**\n\n"

        if not rejected_withdrawals:
            text += "Нет отклоненных заявок."
        else:
            for idx, withdrawal in enumerate(rejected_withdrawals, 1):
                date = withdrawal.created_at.strftime("%d.%m.%Y %H:%M")
                text += f"**{idx}. Заявка #{withdrawal.id}**\n"
                text += f"💰 Сумма: {format_usdt(withdrawal.amount)} USDT\n"
                text += f"👤 Пользователь ID: {withdrawal.user_id}\n"
                text += f"💳 Кошелек: `{withdrawal.to_address}`\n"
                text += f"📅 Дата: {date}\n\n"

        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=admin_withdrawals_keyboard(),
        )

    except Exception as e:
        await session.rollback()
        await message.answer(
            f"❌ Ошибка при загрузке заявок: {str(e)}",
            reply_markup=admin_withdrawals_keyboard(),
        )
