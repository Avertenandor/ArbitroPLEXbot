"""
AI Statistics Service.

Provides comprehensive statistics for AI assistant.
Includes: deposits, bonuses, withdrawals, financial reports.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bonus_credit import BonusCredit
from app.models.deposit import Deposit
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.admin_repository import AdminRepository


class AIStatisticsService:
    """
    AI-powered statistics service.

    Provides comprehensive stats for admin dashboards.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials."""
        if not self.admin_telegram_id:
            return None, "❌ Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin or admin.is_blocked:
            return None, "❌ Администратор не найден или заблокирован"

        return admin, None

    async def get_deposit_stats(self) -> dict[str, Any]:
        """
        Get comprehensive deposit statistics.

        Returns:
            Deposit statistics
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Total deposits from blockchain
        total_stmt = select(func.sum(Deposit.amount)).where(
            Deposit.status == TransactionStatus.CONFIRMED.value
        )
        total_result = await self.session.execute(total_stmt)
        total_deposits = total_result.scalar() or Decimal("0")

        # Count of deposits
        count_stmt = select(func.count(Deposit.id)).where(
            Deposit.status == TransactionStatus.CONFIRMED.value
        )
        count_result = await self.session.execute(count_stmt)
        deposit_count = count_result.scalar() or 0

        # Deposits by level
        level_stmt = (
            select(Deposit.level, func.count(Deposit.id), func.sum(Deposit.amount))
            .where(Deposit.status == TransactionStatus.CONFIRMED.value)
            .group_by(Deposit.level)
            .order_by(Deposit.level)
        )
        level_result = await self.session.execute(level_stmt)
        by_level = [
            {"level": row[0], "count": row[1], "amount": float(row[2] or 0)}
            for row in level_result.all()
        ]

        # Active depositors count
        active_stmt = select(func.count(User.id)).where(
            User.total_deposited_usdt >= 30
        )
        active_result = await self.session.execute(active_stmt)
        active_depositors = active_result.scalar() or 0

        # Pending deposits
        pending_stmt = select(func.count(Deposit.id)).where(
            Deposit.status == TransactionStatus.PENDING.value
        )
        pending_result = await self.session.execute(pending_stmt)
        pending_count = pending_result.scalar() or 0

        return {
            "success": True,
            "deposits": {
                "total_amount": float(total_deposits),
                "total_count": deposit_count,
                "active_depositors": active_depositors,
                "pending_count": pending_count,
            },
            "by_level": by_level,
            "message": "📊 Статистика депозитов"
        }

    async def get_bonus_stats(self) -> dict[str, Any]:
        """
        Get comprehensive bonus statistics.

        Returns:
            Bonus statistics for ALL users
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Total active bonuses
        active_stmt = select(
            func.count(BonusCredit.id),
            func.sum(BonusCredit.amount)
        ).where(BonusCredit.is_active == True)
        active_result = await self.session.execute(active_stmt)
        active_row = active_result.one()
        active_count = active_row[0] or 0
        active_amount = active_row[1] or Decimal("0")

        # Total paid ROI from bonuses
        roi_stmt = select(func.sum(BonusCredit.roi_paid_amount))
        roi_result = await self.session.execute(roi_stmt)
        total_roi_paid = roi_result.scalar() or Decimal("0")

        # Completed bonuses (ROI cap reached)
        completed_stmt = select(func.count(BonusCredit.id)).where(
            BonusCredit.is_roi_completed == True
        )
        completed_result = await self.session.execute(completed_stmt)
        completed_count = completed_result.scalar() or 0

        # Users with active bonuses
        users_stmt = select(func.count(func.distinct(BonusCredit.user_id))).where(
            BonusCredit.is_active == True
        )
        users_result = await self.session.execute(users_stmt)
        users_with_bonus = users_result.scalar() or 0

        # Top bonuses (largest active)
        top_stmt = (
            select(BonusCredit)
            .where(BonusCredit.is_active == True)
            .order_by(BonusCredit.amount.desc())
            .limit(10)
        )
        top_result = await self.session.execute(top_stmt)
        top_bonuses = []
        for bonus in top_result.scalars().all():
            # Get user info
            user_stmt = select(User).where(User.id == bonus.user_id)
            user_result = await self.session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            user_info = f"@{user.username}" if user and user.username else f"ID:{bonus.user_id}"

            top_bonuses.append({
                "id": bonus.id,
                "user": user_info,
                "amount": float(bonus.amount),
                "roi_paid": float(bonus.roi_paid_amount or 0),
                "reason": (bonus.reason or "")[:50],
            })

        return {
            "success": True,
            "bonuses": {
                "active_count": active_count,
                "active_amount": float(active_amount),
                "total_roi_paid": float(total_roi_paid),
                "completed_count": completed_count,
                "users_with_bonus": users_with_bonus,
            },
            "top_bonuses": top_bonuses,
            "message": "🎁 Статистика бонусов"
        }

    async def get_withdrawal_stats(self) -> dict[str, Any]:
        """
        Get withdrawal statistics.

        Returns:
            Withdrawal statistics
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Pending withdrawals
        pending_stmt = select(
            func.count(Transaction.id),
            func.sum(Transaction.amount)
        ).where(
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.PENDING.value,
        )
        pending_result = await self.session.execute(pending_stmt)
        pending_row = pending_result.one()
        pending_count = pending_row[0] or 0
        pending_amount = pending_row[1] or Decimal("0")

        # Completed withdrawals (all time)
        completed_stmt = select(
            func.count(Transaction.id),
            func.sum(Transaction.amount)
        ).where(
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
        )
        completed_result = await self.session.execute(completed_stmt)
        completed_row = completed_result.one()
        completed_count = completed_row[0] or 0
        completed_amount = completed_row[1] or Decimal("0")

        # Today's withdrawals
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        today_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
            Transaction.created_at >= today,
        )
        today_result = await self.session.execute(today_stmt)
        today_amount = today_result.scalar() or Decimal("0")

        # This week
        week_ago = datetime.now(UTC) - timedelta(days=7)
        week_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
            Transaction.created_at >= week_ago,
        )
        week_result = await self.session.execute(week_stmt)
        week_amount = week_result.scalar() or Decimal("0")

        return {
            "success": True,
            "withdrawals": {
                "pending_count": pending_count,
                "pending_amount": float(pending_amount),
                "completed_count": completed_count,
                "completed_amount": float(completed_amount),
                "today_amount": float(today_amount),
                "week_amount": float(week_amount),
            },
            "message": "💸 Статистика выводов"
        }

    async def get_financial_report(self) -> dict[str, Any]:
        """
        Get comprehensive financial report.

        Returns:
            Full financial report
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Total deposits (blockchain)
        deposits_stmt = select(func.sum(Deposit.amount)).where(
            Deposit.status == TransactionStatus.CONFIRMED.value
        )
        deposits_result = await self.session.execute(deposits_stmt)
        total_deposits = deposits_result.scalar() or Decimal("0")

        # Total bonuses active
        bonuses_stmt = select(func.sum(BonusCredit.amount)).where(
            BonusCredit.is_active == True
        )
        bonuses_result = await self.session.execute(bonuses_stmt)
        total_bonuses = bonuses_result.scalar() or Decimal("0")

        # Total ROI paid (rewards)
        rewards_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.type == TransactionType.DEPOSIT_REWARD.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
        )
        rewards_result = await self.session.execute(rewards_stmt)
        total_rewards = rewards_result.scalar() or Decimal("0")

        # Total withdrawals
        withdrawals_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
        )
        withdrawals_result = await self.session.execute(withdrawals_stmt)
        total_withdrawals = withdrawals_result.scalar() or Decimal("0")

        # Pending withdrawals
        pending_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.PENDING.value,
        )
        pending_result = await self.session.execute(pending_stmt)
        pending_withdrawals = pending_result.scalar() or Decimal("0")

        # User balances total
        balances_stmt = select(func.sum(User.balance)).where(User.balance > 0)
        balances_result = await self.session.execute(balances_stmt)
        total_balances = balances_result.scalar() or Decimal("0")

        return {
            "success": True,
            "report": {
                "total_deposits": float(total_deposits),
                "total_bonuses": float(total_bonuses),
                "total_investment": float(total_deposits + total_bonuses),
                "total_rewards_paid": float(total_rewards),
                "total_withdrawals": float(total_withdrawals),
                "pending_withdrawals": float(pending_withdrawals),
                "user_balances": float(total_balances),
            },
            "calculated": {
                "plex_daily_required": int((total_deposits + total_bonuses) * 10),
            },
            "message": "💰 Финансовый отчёт"
        }

    async def get_roi_stats(self) -> dict[str, Any]:
        """
        Get ROI statistics.

        Returns:
            ROI stats
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Total ROI paid from deposits
        deposit_roi_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.type == TransactionType.DEPOSIT_REWARD.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
        )
        deposit_roi_result = await self.session.execute(deposit_roi_stmt)
        total_deposit_roi = deposit_roi_result.scalar() or Decimal("0")

        # Total ROI paid from bonuses
        bonus_roi_stmt = select(func.sum(BonusCredit.roi_paid_amount))
        bonus_roi_result = await self.session.execute(bonus_roi_stmt)
        total_bonus_roi = bonus_roi_result.scalar() or Decimal("0")

        # Today's ROI
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        today_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.type == TransactionType.DEPOSIT_REWARD.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
            Transaction.created_at >= today,
        )
        today_result = await self.session.execute(today_stmt)
        today_roi = today_result.scalar() or Decimal("0")

        return {
            "success": True,
            "roi": {
                "total_deposit_roi": float(total_deposit_roi),
                "total_bonus_roi": float(total_bonus_roi),
                "total_roi": float(total_deposit_roi + total_bonus_roi),
                "today_roi": float(today_roi),
            },
            "message": "📈 Статистика ROI"
        }
