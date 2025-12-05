"""
Deposit Management Reports Handler

Provides deposit reporting functionality:
- Pending deposits overview
- ROI statistics by level
- Active deposit progress tracking
"""

from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.repositories.deposit_repository import DepositRepository
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_deposit_management_keyboard
from bot.utils.formatters import format_usdt

router = Router(name="admin_deposit_management_reports")


@router.message(F.text == "📋 Pending депозиты")
async def show_pending_deposits(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show all pending deposits.

    Args:
        message: Message object
        session: Database session
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    deposit_repo = DepositRepository(session)

    # Get pending deposits
    pending_deposits = await deposit_repo.find_by(
        status=TransactionStatus.PENDING.value
    )

    if not pending_deposits:
        await message.answer(
            "ℹ️ Нет pending депозитов.",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    text = "📋 **Pending депозиты**\n\n"

    for deposit in pending_deposits[:10]:  # Limit to 10
        # Get user info
        user = deposit.user

        text += (
            f"🆔 Deposit ID: `{deposit.id}`\n"
            f"👤 User: {user.telegram_id} (@{user.username or 'N/A'})\n"
            f"📊 Уровень: {deposit.level}\n"
            f"💰 Сумма: {format_usdt(deposit.amount)}\n"
            f"📅 Дата: {deposit.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        )

        if deposit.tx_hash:
            text += f"🔗 TX: `{deposit.tx_hash[:16]}...`\n"

        text += "\n"

    if len(pending_deposits) > 10:
        text += f"\n... и ещё {len(pending_deposits) - 10} депозитов"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_management_keyboard(),
    )


@router.message(F.text == "📈 ROI статистика")
async def show_roi_statistics(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show ROI statistics for all levels.

    Args:
        message: Message object
        session: Database session
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    DepositRepository(session)

    text = "📈 **ROI Статистика**\n\n"

    for level_num in range(1, 6):
        # Get active deposits for this level
        stmt = select(Deposit).where(
            Deposit.level == level_num,
            Deposit.status == TransactionStatus.CONFIRMED.value,
            Deposit.is_roi_completed == False,  # noqa: E712
        )

        result = await session.execute(stmt)
        active_deposits = result.scalars().all()

        if not active_deposits:
            continue

        # Calculate statistics
        total_deposits = len(active_deposits)
        total_paid = sum(d.roi_paid_amount for d in active_deposits)
        total_cap = sum(d.roi_cap_amount for d in active_deposits)
        avg_progress = (total_paid / total_cap * 100) if total_cap > 0 else 0

        # Find deposits close to completion (>80%)
        close_to_completion = [
            d for d in active_deposits
            if (d.roi_paid_amount / d.roi_cap_amount * 100) > 80
        ]

        emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][level_num - 1]
        text += f"{emoji} **Уровень {level_num}:**\n"
        text += f"   Активных: {total_deposits}\n"
        text += f"   Выплачено: {format_usdt(total_paid)}\n"
        text += f"   Средний прогресс: {avg_progress:.1f}%\n"

        if close_to_completion:
            text += f"   🔥 Близки к завершению: {len(close_to_completion)}\n"

        text += "\n"

    if text == "📈 **ROI Статистика**\n\n":
        text += "ℹ️ Нет активных депозитов с незавершённым ROI."

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_management_keyboard(),
    )
