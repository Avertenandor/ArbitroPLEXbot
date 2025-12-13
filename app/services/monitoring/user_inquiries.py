"""User inquiries statistics module for MonitoringService."""

from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.user import User


# Try to import optional models
try:
    from app.models.user_inquiry import UserInquiry

    HAS_INQUIRIES = True
except ImportError:
    HAS_INQUIRIES = False


class UserInquiriesService:
    """Service for collecting user inquiries statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user inquiries service."""
        self.session = session

    async def get_user_inquiries_stats(
        self, limit: int = 20
    ) -> dict[str, Any]:
        """
        Get user inquiries/questions statistics.

        Args:
            limit: Max recent inquiries to return

        Returns:
            Dict with inquiries stats
        """
        if not HAS_INQUIRIES:
            return {
                "available": False,
                "message": "Inquiries module not installed",
            }

        try:
            # Total inquiries
            total_result = await self.session.execute(
                select(func.count(UserInquiry.id))
            )
            total = total_result.scalar() or 0

            # By status
            status_result = await self.session.execute(
                select(
                    UserInquiry.status,
                    func.count(UserInquiry.id),
                ).group_by(UserInquiry.status)
            )
            by_status = {
                row[0]: row[1] for row in status_result.fetchall()
            }

            # Recent inquiries
            recent_result = await self.session.execute(
                select(
                    UserInquiry.id,
                    UserInquiry.initial_question,
                    UserInquiry.status,
                    UserInquiry.created_at,
                    User.username,
                    Admin.username.label("admin_username"),
                )
                .join(User, UserInquiry.user_id == User.id)
                .outerjoin(Admin, UserInquiry.assigned_admin_id == Admin.id)
                .order_by(UserInquiry.created_at.desc())
                .limit(limit)
            )
            recent = [
                {
                    "id": row[0],
                    "question": (
                        (row[1][:100] + "...")
                        if row[1] and len(row[1]) > 100
                        else row[1]
                    ),
                    "status": row[2],
                    "created": (
                        row[3].strftime("%d.%m %H:%M") if row[3] else ""
                    ),
                    "user": row[4] or "Unknown",
                    "assigned_to": row[5] or "Не назначен",
                }
                for row in recent_result.fetchall()
            ]

            return {
                "available": True,
                "total": total,
                "by_status": by_status,
                "new_count": by_status.get("new", 0),
                "in_progress_count": by_status.get("in_progress", 0),
                "closed_count": by_status.get("closed", 0),
                "recent": recent,
            }
        except Exception as e:
            logger.error(f"Error getting inquiries stats: {e}")
            return {"available": True, "error": str(e)}
