"""
Metrics Monitor Service - Anomaly Detector Module.

Module: anomaly_detector.py
Handles anomaly detection using z-score statistical method.
Detects withdrawal, deposit, and balance anomalies.
"""

from typing import Any


class AnomalyDetector:
    """Anomaly detection logic."""

    def __init__(self, z_score_threshold: float, critical_threshold: float) -> None:
        """Initialize anomaly detector."""
        self.z_score_threshold = z_score_threshold
        self.critical_threshold = critical_threshold

    async def detect_anomalies(
        self, current_metrics: dict[str, Any], baseline_manager
    ) -> list[dict[str, Any]]:
        """
        Detect anomalies using z-score method (R14-1).

        Args:
            current_metrics: Current metrics dict
            baseline_manager: Baseline manager for historical data

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Get historical baseline (last 7 days)
        baseline = await baseline_manager.get_historical_baseline(days=7)

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
            if z_score < -self.z_score_threshold:
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

        if abs(z_score) <= self.z_score_threshold:
            return None

        # Determine severity
        if severity:
            final_severity = severity
        elif use_critical_severity:
            final_severity = (
                "critical"
                if abs(z_score) > self.critical_threshold
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
