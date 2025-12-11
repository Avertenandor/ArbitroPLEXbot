"""
Monitoring Service Package.

Provides real-time access to platform metrics, admin activity,
user statistics, financial data, and system health for ARIA AI Assistant.

Usage:
    from app.services.monitoring import MonitoringService, ActivityMonitor

    service = MonitoringService(session)
    dashboard = await service.get_full_dashboard()

    activity = ActivityMonitor(session)
    inquiries = await activity.get_inquiries_stats()
"""

from .activity import ActivityMonitor
from .service import MonitoringService

__all__ = ["MonitoringService", "ActivityMonitor"]
