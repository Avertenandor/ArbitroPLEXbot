"""
Monitoring package for ARIA AI Assistant.

Re-exports MonitoringService for backward compatibility.
"""

from app.services.monitoring.core import MonitoringService

__all__ = ["MonitoringService"]
