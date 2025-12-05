"""
Notification service module.

Provides notification functionality for sending messages to users and admins.

Structure:
- core.py: Core notification service with basic text/photo sending
- admin.py: Admin notification methods
- user_notifications.py: User-specific notifications (withdrawals, ROI)

Usage:
    from app.services.notification import NotificationService

    notification_service = NotificationService(session)
    await notification_service.send_notification(bot, user_id, "Hello!")
    await notification_service.notify_admins(bot, "Alert!")
    await notification_service.notify_withdrawal_processed(telegram_id, amount, tx_hash)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification.admin import AdminNotificationMixin
from app.services.notification.core import NotificationService as CoreNotificationService
from app.services.notification.user_notifications import UserNotificationMixin


class NotificationService(
    CoreNotificationService,
    AdminNotificationMixin,
    UserNotificationMixin,
):
    """
    Combined notification service.

    Inherits from all notification mixins to provide complete functionality.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize notification service with all mixins.

        Args:
            session: Database session
        """
        # Initialize all parent classes
        CoreNotificationService.__init__(self, session)
        AdminNotificationMixin.__init__(self, session)
        UserNotificationMixin.__init__(self, session)


# Export for backward compatibility
__all__ = ["NotificationService"]
