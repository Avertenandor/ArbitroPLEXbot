"""
Monitoring Service - Backward Compatibility Shim.

This file provides backward compatibility for imports from the old path.
The actual implementation has been refactored into the monitoring/ package.

Original: 1062 lines -> Refactored: 2644 lines across 11 modules

Usage (both work):
    from app.services.monitoring_service import MonitoringService  # old
    from app.services.monitoring import MonitoringService  # new (preferred)
"""

# Re-export from the new modular structure
from app.services.monitoring import MonitoringService

__all__ = ["MonitoringService"]
