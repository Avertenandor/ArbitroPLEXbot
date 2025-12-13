"""
Earnings statistics service.

Provides detailed earnings statistics for users including:
- Period-based earnings (today, week, month)
- Total earnings and available balance
- ROI progress for all deposit levels
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import DepositStatus, TransactionStatus
from app.models.transaction import Transaction
from app.models.user import User


class EarningsStatsService:
    """Service for calculating and retrieving earnings statistics."""

    def __init__(self, session: AsyncSession):
        """
        Initialize earnings stats service.

        Args:
            session: Database session
        """
        self.session = session

    async def get_period_earnings(
        self, user_id: int, period_days: int
    ) -> Decimal:
        """
        Get earnings for a specific period.

        Args:
            user_id: User ID
            period_days: Number of days to calculate (1 for today, 7 for week, etc.)

        Returns:
            Total earnings for the period
        """
        try:
            # Calculate start date for period
            start_date = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=period_days - 1)

            # Query transactions for period
            stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.status == TransactionStatus.CONFIRMED.value,
                    Transaction.type.in_(
                        ["deposit_reward", "referral_reward", "system_payout"]
                    ),
                    Transaction.created_at >= start_date.replace(tzinfo=None),
                )
            )

            result = await self.session.execute(stmt)
            total = result.scalar_one()

            return Decimal(str(total)) if total else Decimal("0")

        except Exception as e:
            logger.error(
                f"Failed to get period earnings for user {user_id}, "
                f"period {period_days} days: {e}",
                exc_info=True,
            )
            return Decimal("0")

    async def get_today_earnings(self, user_id: int) -> Decimal:
        """
        Get earnings for today.

        Args:
            user_id: User ID

        Returns:
            Today's earnings
        """
        return await self.get_period_earnings(user_id, 1)

    async def get_week_earnings(self, user_id: int) -> Decimal:
        """
        Get earnings for the last 7 days.

        Args:
            user_id: User ID

        Returns:
            Week's earnings
        """
        return await self.get_period_earnings(user_id, 7)

    async def get_month_earnings(self, user_id: int) -> Decimal:
        """
        Get earnings for the last 30 days.

        Args:
            user_id: User ID

        Returns:
            Month's earnings
        """
        return await self.get_period_earnings(user_id, 30)

    async def get_roi_progress_all_levels(
        self, user_id: int
    ) -> list[dict[str, Any]]:
        """
        Get ROI progress for all active deposits across all levels.

        Args:
            user_id: User ID

        Returns:
            List of ROI progress data for each deposit level with active deposits
        """
        try:
            # Get all active deposits (confirmed and not ROI completed)
            stmt = (
                select(Deposit)
                .where(
                    and_(
                        Deposit.user_id == user_id,
                        Deposit.status == DepositStatus.CONFIRMED.value,
                        Deposit.is_roi_completed == False,  # noqa: E712
                    )
                )
                .order_by(Deposit.level)
            )

            result = await self.session.execute(stmt)
            deposits = result.scalars().all()

            roi_data = []
            for deposit in deposits:
                # Calculate progress percentage
                roi_percent = 0.0
                if deposit.roi_cap_amount > 0:
                    roi_percent = float(
                        (deposit.roi_paid_amount / deposit.roi_cap_amount) * 100
                    )

                roi_remaining = deposit.roi_cap_amount - deposit.roi_paid_amount

                roi_data.append(
                    {
                        "level": deposit.level,
                        "deposit_id": deposit.id,
                        "deposit_amount": deposit.amount,
                        "roi_cap": deposit.roi_cap_amount,
                        "roi_paid": deposit.roi_paid_amount,
                        "roi_remaining": roi_remaining,
                        "roi_percent": roi_percent,
                        "is_completed": deposit.is_roi_completed,
                    }
                )

            return roi_data

        except Exception as e:
            logger.error(
                f"Failed to get ROI progress for user {user_id}: {e}",
                exc_info=True,
            )
            return []

    async def get_full_earnings_stats(self, user_id: int) -> dict[str, Any]:
        """
        Get complete earnings statistics for user.

        Includes:
        - Period earnings (today, week, month)
        - Total earned, pending, and available balance
        - ROI progress for all levels

        Args:
            user_id: User ID

        Returns:
            Dictionary with all earnings statistics
        """
        try:
            # Get user data
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"User {user_id} not found for earnings stats")
                return {}

            # Get period earnings
            today_earnings = await self.get_today_earnings(user_id)
            week_earnings = await self.get_week_earnings(user_id)
            month_earnings = await self.get_month_earnings(user_id)

            # Get ROI progress
            roi_progress = await self.get_roi_progress_all_levels(user_id)

            # Get total paid withdrawals
            stmt_paid = select(
                func.coalesce(func.sum(Transaction.amount), 0)
            ).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.status == TransactionStatus.CONFIRMED.value,
                    Transaction.type == "withdrawal",
                )
            )
            result_paid = await self.session.execute(stmt_paid)
            total_paid = result_paid.scalar_one()

            return {
                # Period earnings
                "today": today_earnings,
                "week": week_earnings,
                "month": month_earnings,
                # Balances
                "total_earned": user.total_earned,
                "pending_earnings": user.pending_earnings,
                "available_balance": user.balance,
                "total_paid": Decimal(str(total_paid)) if total_paid else Decimal("0"),
                # ROI progress
                "roi_progress": roi_progress,
                # User info
                "user_id": user_id,
                "username": user.username,
            }

        except Exception as e:
            logger.error(
                f"Failed to get full earnings stats for user {user_id}: {e}",
                exc_info=True,
            )
            return {}

    async def get_earnings_breakdown_by_type(
        self, user_id: int, period_days: int | None = None
    ) -> dict[str, Decimal]:
        """
        Get earnings breakdown by transaction type.

        Args:
            user_id: User ID
            period_days: Number of days (None for all time)

        Returns:
            Dictionary with earnings by type
        """
        try:
            # Build base query
            conditions = [
                Transaction.user_id == user_id,
                Transaction.status == TransactionStatus.CONFIRMED.value,
                Transaction.type.in_(
                    ["deposit_reward", "referral_reward", "system_payout"]
                ),
            ]

            # Add period filter if specified
            if period_days is not None:
                start_date = datetime.now(UTC).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=period_days - 1)
                conditions.append(
                    Transaction.created_at >= start_date.replace(tzinfo=None)
                )

            # Query by type
            stmt = (
                select(
                    Transaction.type,
                    func.coalesce(func.sum(Transaction.amount), 0).label("total"),
                )
                .where(and_(*conditions))
                .group_by(Transaction.type)
            )

            result = await self.session.execute(stmt)
            rows = result.all()

            # Build breakdown dictionary
            breakdown = {
                "deposit_reward": Decimal("0"),
                "referral_reward": Decimal("0"),
                "system_payout": Decimal("0"),
            }

            for row in rows:
                breakdown[row.type] = Decimal(str(row.total))

            return breakdown

        except Exception as e:
            logger.error(
                f"Failed to get earnings breakdown for user {user_id}: {e}",
                exc_info=True,
            )
            return {
                "deposit_reward": Decimal("0"),
                "referral_reward": Decimal("0"),
                "system_payout": Decimal("0"),
            }
