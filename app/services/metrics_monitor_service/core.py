"""
Metrics Monitor Service - Core Module.

Module: core.py
Contains the main service class and current metrics collection.
Monitors financial metrics and detects anomalies using statistical methods.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus, TransactionType
from app.repositories.deposit_repository import DepositRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository


class MetricsMonitorCore:
    """Core metrics monitoring functionality."""

    # Z-score threshold for anomaly detection
    Z_SCORE_THRESHOLD = 3.0

    # Critical severity threshold (triggers automatic actions)
    CRITICAL_SEVERITY_THRESHOLD = 5.0

    def __init__(self, session: AsyncSession) -> None:
        """Initialize metrics monitor core."""
        self.session = session
        self.user_repo = UserRepository(session)
        self.deposit_repo = DepositRepository(session)
        self.transaction_repo = TransactionRepository(session)

    async def collect_current_metrics(self) -> dict[str, Any]:
        """
        Collect current financial metrics (R14-1).

        Returns:
            Dict with current metrics
        """
        now = datetime.now(UTC)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Import data fetchers to avoid circular dependency
        from .data_fetchers import MetricsDataFetcher
        fetcher = MetricsDataFetcher(
            self.session, self.transaction_repo,
            self.deposit_repo, self.user_repo
        )

        # Withdrawal metrics
        pending_withdrawals = await self.transaction_repo.find_by(
            type=TransactionType.WITHDRAWAL.value,
            status=TransactionStatus.PENDING.value,
        )
        pending_count = len(pending_withdrawals) if pending_withdrawals else 0

        # Withdrawals in last hour
        withdrawals_last_hour = await fetcher.get_withdrawals_in_period(
            hour_ago, now
        )
        withdrawal_amount_last_hour = float(sum(
            w.amount for w in withdrawals_last_hour
        ))

        # Rejected withdrawals (in last hour)
        rejected_count = len([
            w for w in withdrawals_last_hour
            if w.status == TransactionStatus.FAILED.value
        ])

        total_withdrawals = (
            len(withdrawals_last_hour) if withdrawals_last_hour else 0
        )
        rejection_rate = (
            (rejected_count / total_withdrawals * 100)
            if total_withdrawals > 0
            else 0
        )

        # Deposit metrics
        deposits_last_day = await fetcher.get_deposits_in_period(day_ago, now)
        deposit_count = len(deposits_last_day) if deposits_last_day else 0

        # Level 5 deposits (max level)
        level_5_deposits = [
            d for d in deposits_last_day if d.level == 5
        ]
        level_5_count = len(level_5_deposits)

        # Balance metrics
        total_balance = await fetcher.get_total_user_balance()
        total_deposits = await fetcher.get_total_confirmed_deposits()
        total_withdrawals_all = await fetcher.get_total_confirmed_withdrawals()

        # Referral metrics
        referral_earnings = await fetcher.get_referral_earnings_last_day(day_ago)

        return {
            "timestamp": now.isoformat(),
            "withdrawals": {
                "pending_count": pending_count,
                "last_hour_count": len(withdrawals_last_hour)
                if withdrawals_last_hour
                else 0,
                "last_hour_amount": withdrawal_amount_last_hour,
                "rejected_count": rejected_count,
                "rejection_rate": rejection_rate,
            },
            "deposits": {
                "last_day_count": deposit_count,
                "level_5_count": level_5_count,
            },
            "balance": {
                "total_user_balance": float(total_balance),
                "total_deposits": float(total_deposits),
                "total_withdrawals": float(total_withdrawals_all),
                "system_liabilities": float(total_balance),
            },
            "referrals": {
                "earnings_last_day": float(referral_earnings),
            },
        }
