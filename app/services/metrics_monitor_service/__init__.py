"""
Metrics Monitor Service - Main Module.

This module monitors financial metrics and detects anomalies using statistical methods.

Module Structure:
- core.py: Main service class and metrics collection
- anomaly_detector.py: Anomaly detection using z-score method
- baseline.py: Historical baseline calculation
- data_fetchers.py: Database query helpers

Public Interface:
- MetricsMonitorService: Main service class (backward compatible)

Detects anomalies in:
- Withdrawal metrics (pending count, amounts, rejection rate)
- Deposit metrics (count, level 5 deposits)
- Balance metrics (system liabilities)
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .anomaly_detector import AnomalyDetector
from .baseline import BaselineManager
from .core import MetricsMonitorCore
from .data_fetchers import MetricsDataFetcher


class MetricsMonitorService:
    """
    Service for monitoring financial metrics and detecting anomalies.

    This is the main service class that provides backward compatibility
    with the original monolithic implementation.
    """

    # Z-score threshold for anomaly detection
    Z_SCORE_THRESHOLD = 3.0

    # Critical severity threshold (triggers automatic actions)
    CRITICAL_SEVERITY_THRESHOLD = 5.0

    def __init__(self, session: AsyncSession) -> None:
        """Initialize metrics monitor service."""
        self.session = session

        # Initialize all components
        self.core = MetricsMonitorCore(session)
        self.anomaly_detector = AnomalyDetector(
            self.Z_SCORE_THRESHOLD,
            self.CRITICAL_SEVERITY_THRESHOLD
        )
        self.data_fetcher = MetricsDataFetcher(
            session,
            self.core.transaction_repo,
            self.core.deposit_repo,
            self.core.user_repo
        )
        self.baseline_manager = BaselineManager(
            session,
            self.core.transaction_repo,
            self.core.deposit_repo,
            self.core.user_repo,
            self.data_fetcher
        )

        # Expose repositories for backward compatibility
        self.user_repo = self.core.user_repo
        self.deposit_repo = self.core.deposit_repo
        self.transaction_repo = self.core.transaction_repo

    # Delegate methods to appropriate components for backward compatibility

    async def collect_current_metrics(self) -> dict[str, Any]:
        """Collect current financial metrics (R14-1)."""
        return await self.core.collect_current_metrics()

    async def detect_anomalies(
        self, current_metrics: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect anomalies using z-score method (R14-1)."""
        return await self.anomaly_detector.detect_anomalies(
            current_metrics, self.baseline_manager
        )


# Re-export for backward compatibility
__all__ = ['MetricsMonitorService']
