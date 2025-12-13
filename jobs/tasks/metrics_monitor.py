"""
Metrics Monitor Task (R14-1).

Monitors financial metrics and detects anomalies.
Runs every 5 minutes.
"""

import asyncio
from typing import Any

import dramatiq
from aiogram import Bot
from loguru import logger

from app.config.operational_constants import DRAMATIQ_TIME_LIMIT_MEDIUM
from app.config.settings import settings
from app.services.metrics_monitor_service import MetricsMonitorService
from app.services.notification_service import NotificationService
from jobs.async_runner import run_async
from jobs.utils.database import task_engine, task_session_maker


@dramatiq.actor(max_retries=3, time_limit=DRAMATIQ_TIME_LIMIT_MEDIUM)  # 2 min timeout
def monitor_metrics() -> None:
    """
    Monitor financial metrics and detect anomalies (R14-1).
    """
    logger.debug("Starting metrics monitoring...")

    try:
        run_async(_monitor_metrics_async())

    except Exception as e:
        logger.exception(f"Metrics monitoring failed: {e}")


async def _monitor_metrics_async() -> dict:
    """Async implementation of metrics monitoring."""
    try:
        async with task_session_maker() as session:
            metrics_service = MetricsMonitorService(session)

            # Collect current metrics
            current_metrics = await metrics_service.collect_current_metrics()

            # Detect anomalies
            anomalies = await metrics_service.detect_anomalies(current_metrics)

            if anomalies:
                logger.warning(
                    f"Detected {len(anomalies)} anomalies",
                    extra={"anomalies": anomalies},
                )

                # Send alerts for each anomaly
                await _send_anomaly_alerts(anomalies, current_metrics)

                # Take protective actions for critical anomalies
                critical_anomalies = [
                    a
                    for a in anomalies
                    if a.get("severity") == "critical"
                ]
                if critical_anomalies:
                    await _take_protective_actions(critical_anomalies)

            return {
                "success": True,
                "metrics": current_metrics,
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies,
            }
    except asyncio.CancelledError:
        logger.info("Metrics monitoring task cancelled")
        raise
    except Exception as e:
        logger.exception(f"Metrics monitoring task failed: {e}")
        raise
    finally:
        await task_engine.dispose()


async def _send_anomaly_alerts(
    anomalies: list[dict[str, Any]], metrics: dict[str, Any]
) -> None:
    """Send anomaly alerts to admins (R14-1)."""
    bot = None
    try:
        bot = Bot(token=settings.telegram_bot_token)

        try:
            async with task_session_maker() as session:
                notification_service = NotificationService(session)

                admin_ids = settings.get_admin_ids()

                for anomaly in anomalies:
                    anomaly_type = anomaly.get("type", "unknown")
                    current = anomaly.get("current", 0)
                    expected = anomaly.get("expected_mean", 0)
                    z_score = anomaly.get("z_score", 0)
                    severity = anomaly.get("severity", "medium")

                    deviation_pct = (
                        ((current - expected) / expected * 100)
                        if expected > 0
                        else 0
                    )

                    message = (
                        f"🚨 **ANOMALY DETECTED: {anomaly_type}**\n\n"
                        f"**Severity:** {severity.upper()}\n"
                        f"**Current:** {current}\n"
                        f"**Expected:** {expected:.2f}\n"
                        f"**Deviation:** {deviation_pct:+.1f}%\n"
                        f"**Z-score:** {z_score:.2f}\n\n"
                        f"**Timestamp:** {metrics.get('timestamp', 'N/A')}"
                    )

                    # Add recommendations
                    if anomaly_type == "withdrawal_pending_spike":
                        message += (
                            "\n\n**Recommended Actions:**\n"
                            "- Review pending withdrawals manually\n"
                            "- Consider temporary pause of auto-approvals"
                        )
                    elif anomaly_type == "withdrawal_amount_spike":
                        message += (
                            "\n\n**Recommended Actions:**\n"
                            "- Require two super_admin approvals for large withdrawals\n"
                            "- Enhanced fraud detection for new operations"
                        )

                    for admin_id in admin_ids:
                        await notification_service.send_notification(
                            bot, admin_id, message, critical=(severity == "critical")
                        )
        finally:
            await task_engine.dispose()

    except Exception as e:
        logger.error(f"Error sending anomaly alerts: {e}")
    finally:
        if bot:
            await bot.session.close()


async def _take_protective_actions(
    anomalies: list[dict[str, Any]]
) -> None:
    """
    Take automatic protective actions for critical anomalies (R14-1).

    Args:
        anomalies: List of critical anomalies
    """
    logger.warning(
        f"Taking protective actions for {len(anomalies)} critical anomalies"
    )

    # In production, would implement:
    # - Temporary pause of auto-approvals for withdrawals >$1000
    # - Require two super_admin for large withdrawals
    # - Enhanced fraud detection

    for anomaly in anomalies:
        anomaly_type = anomaly.get("type", "unknown")
        logger.info(
            f"Protective action triggered for: {anomaly_type}",
            extra={"anomaly": anomaly},
        )
