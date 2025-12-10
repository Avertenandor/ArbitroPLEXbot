"""
Metrics Monitor Service (R14-1).

Monitors financial metrics and detects anomalies using statistical methods.

This module maintains backward compatibility by re-exporting
from the refactored modular structure.
"""

# Re-export from modular structure for backward compatibility
from app.services.metrics_monitor_service import MetricsMonitorService


__all__ = ['MetricsMonitorService']
