"""
User Activity Service.

Complete service combining all modules for tracking and analyzing
user activities.
"""

from app.services.user_activity.analytics import (
    UserActivityAnalyticsMixin,
)
from app.services.user_activity.core import UserActivityServiceCore
from app.services.user_activity.maintenance import (
    UserActivityMaintenanceMixin,
)
from app.services.user_activity.tracking import (
    UserActivityTrackingMixin,
)


class UserActivityService(
    UserActivityServiceCore,
    UserActivityTrackingMixin,
    UserActivityAnalyticsMixin,
    UserActivityMaintenanceMixin,
):
    """
    Complete service for tracking and analyzing user activities.

    Combines functionality from:
    - Core: Configuration and basic logging
    - Tracking: Specific activity logging methods
    - Analytics: Statistics and reporting
    - Maintenance: Cleanup and record management
    """


__all__ = ["UserActivityService"]
