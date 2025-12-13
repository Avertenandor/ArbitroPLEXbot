"""
Monitoring Service for ARIA AI Assistant.

This module provides backward compatibility by re-exporting
MonitoringService from the new monitoring package.

The service has been refactored into multiple modules:
- app/services/monitoring/core.py - Main MonitoringService class
- app/services/monitoring/admin_stats.py - Admin statistics
- app/services/monitoring/user_stats.py - User statistics
- app/services/monitoring/financial_stats.py - Financial statistics
- app/services/monitoring/system_health.py - System health checks
- app/services/monitoring/user_inquiries.py - User inquiries stats
- app/services/monitoring/activity.py - User activity analytics
- app/services/monitoring/formatters.py - Data formatting for AI
"""

from app.services.monitoring import MonitoringService

__all__ = ["MonitoringService"]
