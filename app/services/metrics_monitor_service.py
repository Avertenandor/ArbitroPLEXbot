"""
Metrics Monitor Service (R14-1).

Monitors financial metrics and detects anomalies using statistical methods.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.repositories.deposit_repository import DepositRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository


class MetricsMonitorService:
    """Service for monitoring financial metrics and detecting anomalies."""

    # Z-score threshold for anomaly detection
    Z_SCORE_THRESHOLD = 3.0

    # Critical severity threshold (triggers automatic actions)
    CRITICAL_SEVERITY_THRESHOLD = 5.0

    def __init__(self, session: AsyncSession) -> None:
        """Initialize metrics monitor service."""
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

        # Withdrawal metrics
        pending_withdrawals = await self.transaction_repo.find_by(
            type=TransactionType.WITHDRAWAL.value,
            status=TransactionStatus.PENDING.value,
        )
        pending_count = len(pending_withdrawals) if pending_withdrawals else 0

        # Withdrawals in last hour
        withdrawals_last_hour = await self._get_withdrawals_in_period(
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
        deposits_last_day = await self._get_deposits_in_period(day_ago, now)
        deposit_count = len(deposits_last_day) if deposits_last_day else 0

        # Level 5 deposits (max level)
        level_5_deposits = [
            d for d in deposits_last_day if d.level == 5
        ]
        level_5_count = len(level_5_deposits)

        # Balance metrics
        total_balance = await self._get_total_user_balance()
        total_deposits = await self._get_total_confirmed_deposits()
        total_withdrawals_all = await self._get_total_confirmed_withdrawals()

        # Referral metrics
        referral_earnings = await self._get_referral_earnings_last_day(day_ago)

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

    async def detect_anomalies(
        self, current_metrics: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Detect anomalies using z-score method (R14-1).

        Args:
            current_metrics: Current metrics dict

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Get historical baseline (last 7 days)
        baseline = await self._get_historical_baseline(days=7)

        # Check each metric category
        anomalies.extend(self._check_withdrawal_anomalies(current_metrics, baseline))
        anomalies.extend(self._check_deposit_anomalies(current_metrics, baseline))
        anomalies.extend(self._check_balance_anomalies(current_metrics, baseline))

        return anomalies

    def _check_withdrawal_anomalies(
        self, current_metrics: dict[str, Any], baseline: dict[str, float]
    ) -> list[dict[str, Any]]:
        """Check withdrawal-related anomalies."""
        anomalies = []

        if "withdrawals" not in current_metrics:
            return anomalies

        w_metrics = current_metrics["withdrawals"]

        # Pending withdrawals spike
        anomaly = self._check_metric_anomaly(
            metric_value=w_metrics.get("pending_count"),
            baseline_mean_key="pending_withdrawals_mean",
            baseline_std_key="pending_withdrawals_std",
            baseline=baseline,
            anomaly_type="withdrawal_pending_spike",
            metric_name="pending_withdrawals",
            default_mean=0,
            default_std=1,
            use_critical_severity=True,
        )
        if anomaly:
            anomalies.append(anomaly)

        # Withdrawal amount spike
        anomaly = self._check_metric_anomaly(
            metric_value=w_metrics.get("last_hour_amount"),
            baseline_mean_key="withdrawal_amount_mean",
            baseline_std_key="withdrawal_amount_std",
            baseline=baseline,
            anomaly_type="withdrawal_amount_spike",
            metric_name="withdrawal_amount",
            default_mean=0,
            default_std=1,
            use_critical_severity=True,
        )
        if anomaly:
            anomalies.append(anomaly)

        # Rejection rate spike
        anomaly = self._check_metric_anomaly(
            metric_value=w_metrics.get("rejection_rate"),
            baseline_mean_key="rejection_rate_mean",
            baseline_std_key="rejection_rate_std",
            baseline=baseline,
            anomaly_type="rejection_rate_spike",
            metric_name="rejection_rate",
            default_mean=2.0,
            default_std=1.0,
            severity="high",
        )
        if anomaly:
            anomalies.append(anomaly)

        return anomalies

    def _check_deposit_anomalies(
        self, current_metrics: dict[str, Any], baseline: dict[str, float]
    ) -> list[dict[str, Any]]:
        """Check deposit-related anomalies."""
        anomalies = []

        if "deposits" not in current_metrics:
            return anomalies

        d_metrics = current_metrics["deposits"]

        # Low deposit count (check for negative z-score)
        if "last_day_count" in d_metrics:
            z_score = self._calculate_z_score(
                d_metrics["last_day_count"],
                baseline.get("deposit_count_mean", 50),
                baseline.get("deposit_count_std", 10),
            )
            if z_score < -self.Z_SCORE_THRESHOLD:
                anomalies.append(
                    {
                        "type": "deposit_count_low",
                        "metric": "deposit_count",
                        "current": d_metrics["last_day_count"],
                        "expected_mean": baseline.get("deposit_count_mean", 50),
                        "z_score": z_score,
                        "severity": "medium",
                    }
                )

        # Level 5 spike
        anomaly = self._check_metric_anomaly(
            metric_value=d_metrics.get("level_5_count"),
            baseline_mean_key="level_5_count_mean",
            baseline_std_key="level_5_count_std",
            baseline=baseline,
            anomaly_type="level_5_deposit_spike",
            metric_name="level_5_deposits",
            default_mean=5,
            default_std=2,
            severity="high",
        )
        if anomaly:
            anomalies.append(anomaly)

        return anomalies

    def _check_balance_anomalies(
        self, current_metrics: dict[str, Any], baseline: dict[str, float]
    ) -> list[dict[str, Any]]:
        """Check balance-related anomalies."""
        anomalies = []

        if "balance" not in current_metrics:
            return anomalies

        b_metrics = current_metrics["balance"]

        # System liabilities spike
        anomaly = self._check_metric_anomaly(
            metric_value=b_metrics.get("system_liabilities"),
            baseline_mean_key="system_liabilities_mean",
            baseline_std_key="system_liabilities_std",
            baseline=baseline,
            anomaly_type="system_liabilities_spike",
            metric_name="system_liabilities",
            default_mean=0,
            default_std=1000,
            use_critical_severity=True,
        )
        if anomaly:
            anomalies.append(anomaly)

        return anomalies

    def _check_metric_anomaly(
        self,
        metric_value: float | None,
        baseline_mean_key: str,
        baseline_std_key: str,
        baseline: dict[str, float],
        anomaly_type: str,
        metric_name: str,
        default_mean: float,
        default_std: float,
        severity: str | None = None,
        use_critical_severity: bool = False,
    ) -> dict[str, Any] | None:
        """
        Check if a metric shows anomalous behavior.

        Args:
            metric_value: Current metric value
            baseline_mean_key: Key for baseline mean
            baseline_std_key: Key for baseline std dev
            baseline: Baseline data dictionary
            anomaly_type: Type identifier for anomaly
            metric_name: Human-readable metric name
            default_mean: Default mean if not in baseline
            default_std: Default std dev if not in baseline
            severity: Fixed severity level (or None for dynamic)
            use_critical_severity: Whether to use critical threshold

        Returns:
            Anomaly dict or None if no anomaly detected
        """
        if metric_value is None:
            return None

        z_score = self._calculate_z_score(
            metric_value,
            baseline.get(baseline_mean_key, default_mean),
            baseline.get(baseline_std_key, default_std),
        )

        if abs(z_score) <= self.Z_SCORE_THRESHOLD:
            return None

        # Determine severity
        if severity:
            final_severity = severity
        elif use_critical_severity:
            final_severity = (
                "critical"
                if abs(z_score) > self.CRITICAL_SEVERITY_THRESHOLD
                else "high"
            )
        else:
            final_severity = "high"

        return {
            "type": anomaly_type,
            "metric": metric_name,
            "current": metric_value,
            "expected_mean": baseline.get(baseline_mean_key, default_mean),
            "z_score": z_score,
            "severity": final_severity,
        }

    def _calculate_z_score(
        self, value: float, mean: float, std_dev: float
    ) -> float:
        """
        Calculate z-score for anomaly detection.

        Args:
            value: Current value
            mean: Historical mean
            std_dev: Standard deviation

        Returns:
            Z-score
        """
        if std_dev == 0:
            return 0.0

        return (value - mean) / std_dev

    async def _get_historical_baseline(
        self, days: int = 30
    ) -> dict[str, float]:
        """
        Calculate historical baseline from actual data.

        Args:
            days: Number of days to look back (default 30)

        Returns:
            Dict with mean and std_dev for each metric
        """
        import statistics

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
            deposits = await self._get_deposits_in_period(day_start, day_end)
            daily_deposit_counts.append(len(deposits))
            daily_level_5_counts.append(
                len([d for d in deposits if d.level == 5])
            )

            # Withdrawals for this day
            withdrawals = await self._get_withdrawals_in_period(day_start, day_end)
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
        system_liabilities = float(await self._get_total_user_balance())

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

    async def _get_withdrawals_in_period(
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

    async def _get_deposits_in_period(
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

    async def _get_total_user_balance(self) -> Decimal:
        """Get total user balance."""
        stmt = select(func.sum(self.user_repo.model.balance))
        result = await self.session.execute(stmt)
        total = result.scalar() or Decimal("0")
        return total

    async def _get_total_confirmed_deposits(self) -> Decimal:
        """Get total confirmed deposits."""
        deposits = await self.deposit_repo.find_by(
            status=TransactionStatus.CONFIRMED.value,
        )
        if not deposits:
            return Decimal("0")

        return sum(d.amount for d in deposits)

    async def _get_total_confirmed_withdrawals(self) -> Decimal:
        """Get total confirmed withdrawals."""
        withdrawals = await self.transaction_repo.find_by(
            type=TransactionType.WITHDRAWAL.value,
            status=TransactionStatus.CONFIRMED.value,
        )
        if not withdrawals:
            return Decimal("0")

        return sum(Decimal(str(w.amount)) for w in withdrawals)

    async def _get_referral_earnings_last_day(
        self, day_ago: datetime
    ) -> Decimal:
        """Get referral earnings in last day."""
        # Simplified - would need referral_earnings table
        return Decimal("0")
