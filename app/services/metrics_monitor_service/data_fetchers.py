"""
Metrics Monitor Service - Data Fetchers Module.

Module: data_fetchers.py
Contains database query helper methods.
Fetches withdrawal, deposit, balance, and referral data.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction


class MetricsDataFetcher:
    """Database query helpers for metrics."""

    def __init__(self, session, transaction_repo, deposit_repo, user_repo) -> None:
        """Initialize data fetcher."""
        self.session = session
        self.transaction_repo = transaction_repo
        self.deposit_repo = deposit_repo
        self.user_repo = user_repo

    async def get_withdrawals_in_period(
        self, start: datetime, end: datetime
    ) -> list[Transaction]:
        """Get withdrawals in time period."""
        # Convert to naive datetime for Transaction model (TIMESTAMP WITHOUT TIME ZONE)
        start_naive = start.replace(tzinfo=None) if start.tzinfo else start
        end_naive = end.replace(tzinfo=None) if end.tzinfo else end

        stmt = (
            select(Transaction)
            .where(Transaction.type == TransactionType.WITHDRAWAL.value)
            .where(Transaction.created_at >= start_naive)
            .where(Transaction.created_at < end_naive)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_deposits_in_period(
        self, start: datetime, end: datetime
    ) -> list[Deposit]:
        """Get deposits in time period."""
        deposits = await self.deposit_repo.find_by(
            status=TransactionStatus.CONFIRMED.value,
        )
        if not deposits:
            return []

        return [
            d
            for d in deposits
            if d.created_at >= start and d.created_at < end
        ]

    async def get_total_user_balance(self) -> Decimal:
        """Get total user balance."""
        stmt = select(func.sum(self.user_repo.model.balance))
        result = await self.session.execute(stmt)
        total = result.scalar() or Decimal("0")
        return total

    async def get_total_confirmed_deposits(self) -> Decimal:
        """Get total confirmed deposits."""
        deposits = await self.deposit_repo.find_by(
            status=TransactionStatus.CONFIRMED.value,
        )
        if not deposits:
            return Decimal("0")

        return sum(d.amount for d in deposits)

    async def get_total_confirmed_withdrawals(self) -> Decimal:
        """Get total confirmed withdrawals."""
        withdrawals = await self.transaction_repo.find_by(
            type=TransactionType.WITHDRAWAL.value,
            status=TransactionStatus.CONFIRMED.value,
        )
        if not withdrawals:
            return Decimal("0")

        return sum(Decimal(str(w.amount)) for w in withdrawals)

    async def get_referral_earnings_last_day(
        self, day_ago: datetime
    ) -> Decimal:
        """Get referral earnings in last day."""
        # Simplified - would need referral_earnings table
        return Decimal("0")
