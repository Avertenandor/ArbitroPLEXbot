"""
Deposit Management Menu Handler

Provides the main deposit management menu and general statistics:
- Main deposit management menu
- Comprehensive deposit statistics by level
- Total deposits and amounts overview
"""

from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.repositories.deposit_repository import DepositRepository
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_deposit_management_keyboard
from bot.utils.formatters import format_usdt


router = Router(name="admin_deposit_management_menu")


@router.message(F.text == "💰 Управление депозитами")
async def show_deposit_management_menu(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show deposit management main menu.

    Args:
        message: Message object
        session: Database session
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    text = """
💰 **Управление депозитами**

Выберите действие:
    """.strip()

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_management_keyboard(),
    )


@router.message(F.text == "📊 Статистика по депозитам")
async def show_deposit_statistics(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show comprehensive deposit statistics.

    Args:
        message: Message object
        session: Database session
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    DepositRepository(session)

    # Get total statistics
    stmt = select(
        func.count(Deposit.id).label("total"),
        func.count(Deposit.id).filter(
            Deposit.status == TransactionStatus.CONFIRMED.value
        ).label("active"),
        func.count(Deposit.id).filter(
            Deposit.is_roi_completed == True  # noqa: E712
        ).label("completed"),
        func.count(Deposit.id).filter(
            Deposit.status == TransactionStatus.PENDING.value
        ).label("pending"),
    )

    result = await session.execute(stmt)
    stats = result.one()

    # Get statistics by level
    level_stats = []
    for level_num in range(1, 6):
        stmt_level = select(
            func.count(Deposit.id).label("count"),
            func.sum(Deposit.amount).label("total_amount"),
        ).where(
            Deposit.level == level_num,
            Deposit.status == TransactionStatus.CONFIRMED.value,
        )

        result_level = await session.execute(stmt_level)
        level_data = result_level.one()

        count = level_data.count or 0
        total_amount = level_data.total_amount or Decimal("0")

        level_stats.append((level_num, count, total_amount))

    # Calculate grand total
    grand_total = sum(amount for _, _, amount in level_stats)

    # Format message
    text = f"""
📊 **Статистика депозитов**

**Общая информация:**
Всего депозитов: {stats.total}
Активных: {stats.active}
Завершенных: {stats.completed}
Pending: {stats.pending}

**По уровням:**
"""

    for level_num, count, total_amount in level_stats:
        emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][level_num - 1]
        text += f"{emoji} Уровень {level_num}: {count} депозитов ({format_usdt(total_amount)})\n"

    text += f"\n💰 **Общая сумма:** {format_usdt(grand_total)}"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_management_keyboard(),
    )
