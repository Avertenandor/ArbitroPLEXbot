"""
Metrics Monitor Service - Baseline Module.

Module: baseline.py
Calculates historical baseline from actual data.
Provides statistical baselines for anomaly detection.
"""

import statistics
from datetime import UTC, datetime, timedelta

from loguru import logger

from app.models.enums import TransactionStatus, TransactionType


class BaselineManager:
    """Historical baseline calculation."""

    def __init__(self, session, transaction_repo, deposit_repo, user_repo, data_fetcher) -> None:
        """Initialize baseline manager."""
        self.session = session
        self.transaction_repo = transaction_repo
        self.deposit_repo = deposit_repo
        self.user_repo = user_repo
        self.data_fetcher = data_fetcher

    async def get_historical_baseline(
        self, days: int = 30
    ) -> dict[str, float]:
        """
        Calculate historical baseline from actual data.

        Args:
            days: Number of days to look back (default 30)

        Returns:
            Dict with mean and std_dev for each metric
        """
        now = datetime.now(UTC)

        # Collect daily metrics for the past N days
        daily_deposit_counts: list[int] = []
        daily_withdrawal_amounts: list[float] = []
        daily_level_5_counts: list[int] = []

        for i in range(days):
            day_start = (now - timedelta(days=i + 1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)

            # Deposits for this day
            deposits = await self.data_fetcher.get_deposits_in_period(day_start, day_end)
            daily_deposit_counts.append(len(deposits))
            daily_level_5_counts.append(
                len([d for d in deposits if d.level == 5])
            )

            # Withdrawals for this day
            withdrawals = await self.data_fetcher.get_withdrawals_in_period(day_start, day_end)
            daily_withdrawal_amounts.append(
                float(sum(w.amount for w in withdrawals))
            )

        # Current pending withdrawals (snapshot metric, not daily)
        pending = await self.transaction_repo.find_by(
            type=TransactionType.WITHDRAWAL.value,
            status=TransactionStatus.PENDING.value,
        )
        pending_count = len(pending) if pending else 0

        # Current system liabilities
        system_liabilities = float(await self.data_fetcher.get_total_user_balance())

        # Calculate statistics with fallback for insufficient data
        def safe_mean(data: list, default: float = 0.0) -> float:
            return statistics.mean(data) if len(data) >= 2 else default

        def safe_stdev(data: list, default: float = 1.0) -> float:
            if len(data) < 2:
                return default
            try:
                return max(statistics.stdev(data), 0.1)  # Minimum 0.1 to avoid div by 0
            except statistics.StatisticsError:
                return default

        # Build baseline from actual data
        deposit_mean = safe_mean(daily_deposit_counts, 0.0)
        deposit_std = safe_stdev(daily_deposit_counts, max(deposit_mean * 0.5, 1.0))

        withdrawal_mean = safe_mean(daily_withdrawal_amounts, 0.0)
        withdrawal_std = safe_stdev(daily_withdrawal_amounts, max(withdrawal_mean * 0.5, 100.0))

        level_5_mean = safe_mean(daily_level_5_counts, 0.0)
        level_5_std = safe_stdev(daily_level_5_counts, max(level_5_mean * 0.5, 1.0))

        logger.debug(
            f"Dynamic baseline calculated from {days} days: "
            f"deposits={deposit_mean:.1f}±{deposit_std:.1f}, "
            f"withdrawals={withdrawal_mean:.1f}±{withdrawal_std:.1f}"
        )

        return {
            # Pending withdrawals - use current as baseline if no history
            "pending_withdrawals_mean": float(pending_count) or 1.0,
            "pending_withdrawals_std": max(float(pending_count) * 0.5, 1.0),
            # Withdrawal amounts from history
            "withdrawal_amount_mean": withdrawal_mean,
            "withdrawal_amount_std": withdrawal_std,
            # Rejection rate - keep reasonable default
            "rejection_rate_mean": 2.0,
            "rejection_rate_std": 2.0,
            # Deposit count from history
            "deposit_count_mean": deposit_mean,
            "deposit_count_std": deposit_std,
            # Level 5 from history
            "level_5_count_mean": level_5_mean,
            "level_5_count_std": level_5_std,
            # System liabilities - use current as baseline
            "system_liabilities_mean": system_liabilities or 1000.0,
            "system_liabilities_std": max(system_liabilities * 0.3, 1000.0),
        }
