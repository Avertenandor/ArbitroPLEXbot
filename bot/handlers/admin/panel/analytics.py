"""
Admin Analytics Handlers

Provides analytics commands for admins:
- /retention - Retention metrics (DAU/WAU/MAU) with cohort analysis
- /dashboard - Quick 24-hour metrics dashboard
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import DepositStatus, TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.utils.formatters import format_balance


router = Router(name="admin_panel_analytics")


@router.message(Command("retention"))
async def cmd_retention(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Retention metrics (DAU/WAU/MAU) for admins.
    Usage: /retention
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from app.services.analytics_service import AnalyticsService

    analytics = AnalyticsService(session)
    metrics = await analytics.get_retention_metrics()
    cohorts = await analytics.get_cohort_stats(days=7)
    avg_deposit = await analytics.get_average_deposit()

    # Build text
    text = (
        f"📈 *Retention-метрики*\n\n"
        f"👥 *Активные пользователи:*\n"
        f"• DAU (24ч): *{metrics['dau']}* ({metrics['dau_rate']}%)\n"
        f"• WAU (7д): *{metrics['wau']}* ({metrics['wau_rate']}%)\n"
        f"• MAU (30д): *{metrics['mau']}* ({metrics['mau_rate']}%)\n"
        f"• Всего: *{metrics['total_users']}*\n\n"
        f"📊 *Stickiness (DAU/MAU):* `{metrics['stickiness']}%`\n\n"
        f"💰 *Депозиты:*\n"
        f"• Средний чек: *{format_balance(avg_deposit['avg_deposit'], decimals=2)} USDT*\n"
        f"• Конверсия в депозит: *{avg_deposit['deposit_rate']}%*\n\n"
        f"📅 *Когорты (последние 7 дней):*\n"
    )

    for cohort in cohorts:
        text += (
            f"• {cohort['date']}: {cohort['registered']} рег → "
            f"{cohort['deposited']} деп ({cohort['conversion_rate']}%)\n"
        )

    await message.answer(text, parse_mode="Markdown")


@router.message(Command("dashboard"))
async def cmd_dashboard(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Quick dashboard with 24h metrics for admins.
    Usage: /dashboard
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    cutoff_24h = datetime.now(UTC) - timedelta(hours=24)
    # Transaction model uses naive datetime (TIMESTAMP WITHOUT TIME ZONE)
    cutoff_24h_naive = cutoff_24h.replace(tzinfo=None)

    # New users in 24h (User model uses timezone-aware datetime)
    stmt = select(func.count(User.id)).where(User.created_at >= cutoff_24h)
    result = await session.execute(stmt)
    new_users_24h = result.scalar() or 0

    # New deposits in 24h
    stmt = select(func.count(Deposit.id), func.coalesce(func.sum(Deposit.amount), 0)).where(
        and_(
            Deposit.created_at >= cutoff_24h,
            Deposit.status == DepositStatus.ACTIVE.value,
        )
    )
    result = await session.execute(stmt)
    row = result.one()
    deposits_24h_count = row[0] or 0
    deposits_24h_amount = float(row[1] or 0)

    # Withdrawals in 24h (use naive datetime for Transaction model)
    stmt = select(func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.created_at >= cutoff_24h_naive,
            Transaction.transaction_type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.COMPLETED.value,
        )
    )
    result = await session.execute(stmt)
    row = result.one()
    withdrawals_24h_count = row[0] or 0
    withdrawals_24h_amount = float(row[1] or 0)

    # Pending withdrawals
    stmt = select(func.count(Transaction.id)).where(
        and_(
            Transaction.transaction_type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.PENDING.value,
        )
    )
    result = await session.execute(stmt)
    pending_withdrawals = result.scalar() or 0

    # Fraud alerts (users with risk_score > 50)
    # Simplified - count banned users as proxy
    stmt = select(func.count(User.id)).where(User.is_banned is True)
    result = await session.execute(stmt)
    fraud_alerts = result.scalar() or 0

    # 📊 Text-based charts
    def make_bar(value: float, max_val: float, length: int = 10) -> str:
        if max_val == 0:
            return "░" * length
        filled = int((value / max_val) * length)
        return "█" * filled + "░" * (length - filled)

    chart = ""
    # Example chart: Deposits vs Withdrawals
    max_vol = max(deposits_24h_amount, withdrawals_24h_amount)
    if max_vol > 0:
        dep_bar = make_bar(deposits_24h_amount, max_vol)
        wd_bar = make_bar(withdrawals_24h_amount, max_vol)
        chart = (
            f"\n📈 *Объем за 24ч:*\n"
            f"📥 Деп: `{dep_bar}` {int(deposits_24h_amount)}$\n"
            f"📤 Выв: `{wd_bar}` {int(withdrawals_24h_amount)}$\n"
        )

    deposits_usdt = format_balance(deposits_24h_amount, decimals=2)
    withdrawals_usdt = format_balance(withdrawals_24h_amount, decimals=2)
    text = (
        f"📊 *Дашборд (за 24ч)*\n\n"
        f"👥 Новых пользователей: *{new_users_24h}*\n"
        f"💰 Депозитов: *{deposits_24h_count}* ({deposits_usdt} USDT)\n"
        f"💸 Выводов: *{withdrawals_24h_count}* "
        f"({withdrawals_usdt} USDT)\n"
        f"⏳ Ожидают одобрения: *{pending_withdrawals}*\n"
        f"🚨 Заблокировано: *{fraud_alerts}*\n"
        f"{chart}\n"
        f"_Обновлено: {datetime.now(UTC).strftime('%H:%M UTC')}_"
    )

    await message.answer(text, parse_mode="Markdown")
