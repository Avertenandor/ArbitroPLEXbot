"""
AI Appeals Service.

Provides appeal management tools for AI assistant with STRICT security:
- Only callable from admin AI assistant context
- Validates admin credentials before every operation
- Full audit logging

SECURITY: This service is ONLY accessible through the AI assistant
when a verified admin is in an authenticated admin session.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appeal import Appeal
from app.services.ai.commons import verify_admin
from app.services.ai_appeals_formatter import (
    format_appeal_details,
    format_appeal_list_item,
)
from app.services.ai_appeals_helpers import (
    count_appeals_by_status,
    fetch_users_batch,
    get_reviewer_info,
    get_user_info,
    validate_status_filter,
)
from app.services.ai_appeals_operations import (
    resolve_appeal_with_decision,
    send_reply_to_appeal,
    take_appeal_for_review,
)
from app.utils.formatters import format_user_identifier


class AIAppealsService:
    """
    AI-powered appeals management service.

    SECURITY NOTES:
    - admin_data MUST come from authenticated admin session
    - All operations are logged with admin info
    - Only admins can perform actions
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}

        # Extract admin info for security logging
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username") or self.admin_data.get("Имя")

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """
        Verify admin credentials from session data.

        Returns:
            Tuple of (admin_model, error_message)
        """
        return await verify_admin(self.session, self.admin_telegram_id)

    async def get_appeals_list(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get list of appeals with optional status filter.

        Args:
            status: Filter by status (pending, under_review, approved, rejected)
            limit: Maximum number of appeals to return

        Returns:
            Result dict with appeals list
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Build query - no joinedload since Appeal doesn't have user relationship
        stmt = (
            select(Appeal)
            .order_by(Appeal.created_at.desc())
            .limit(limit)
        )

        # Validate status filter
        is_valid, error_msg = validate_status_filter(status)
        if not is_valid:
            return {"success": False, "error": error_msg}

        if status:
            stmt = stmt.where(Appeal.status == status.lower())

        result = await self.session.execute(stmt)
        appeals = list(result.scalars().all())

        if not appeals:
            status_text = f" со статусом '{status}'" if status else ""
            return {
                "success": True,
                "appeals": [],
                "message": f"ℹ️ Обращений{status_text} не найдено"
            }

        # Fetch users in batch
        user_ids = [a.user_id for a in appeals if a.user_id]
        users_map = await fetch_users_batch(self.session, user_ids)

        # Format appeals
        appeals_list = []
        for a in appeals:
            # Get user info
            user = users_map.get(a.user_id)
            if user:
                user_info = format_user_identifier(user)
            else:
                user_info = f"User#{a.user_id}"

            # Format appeal using formatter
            appeal_item = format_appeal_list_item(a, user_info)
            appeals_list.append(appeal_item)

        # Count by status
        counts = await count_appeals_by_status(self.session)

        return {
            "success": True,
            "total_count": len(appeals_list),
            "counts": counts,
            "appeals": appeals_list,
            "message": f"📋 Найдено {len(appeals_list)} обращений"
        }

    async def get_appeal_details(
        self,
        appeal_id: int,
    ) -> dict[str, Any]:
        """
        Get detailed information about a specific appeal.

        Args:
            appeal_id: Appeal ID

        Returns:
            Result dict with appeal details
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Get appeal
        stmt = select(Appeal).where(Appeal.id == appeal_id)
        result = await self.session.execute(stmt)
        appeal = result.scalar_one_or_none()

        if not appeal:
            error_text = f"❌ Обращение ID {appeal_id} не найдено"
            return {"success": False, "error": error_text}

        # Get user and reviewer info
        user_info, user_telegram = await get_user_info(
            self.session,
            appeal.user_id
        )
        reviewer_info = await get_reviewer_info(
            self.session,
            appeal.reviewed_by_admin_id
        )

        # Format appeal details
        appeal_dict = format_appeal_details(
            appeal,
            user_info,
            user_telegram,
            reviewer_info
        )

        return {
            "success": True,
            "appeal": appeal_dict,
            "message": f"📋 Обращение #{appeal.id}"
        }

    async def take_appeal(
        self,
        appeal_id: int,
    ) -> dict[str, Any]:
        """
        Take appeal for review (set status to under_review).

        Args:
            appeal_id: Appeal ID

        Returns:
            Result dict
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        return await take_appeal_for_review(
            self.session,
            admin,
            appeal_id
        )

    async def resolve_appeal(
        self,
        appeal_id: int,
        decision: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Resolve appeal (approve or reject).

        SECURITY: Only admins can resolve appeals.

        Args:
            appeal_id: Appeal ID
            decision: "approve" or "reject"
            notes: Optional review notes

        Returns:
            Result dict
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        return await resolve_appeal_with_decision(
            self.session,
            admin,
            appeal_id,
            decision,
            notes
        )

    async def reply_to_appeal(
        self,
        appeal_id: int,
        message: str,
        bot: Any = None,
    ) -> dict[str, Any]:
        """
        Send reply message to user who submitted the appeal.

        Args:
            appeal_id: Appeal ID
            message: Message text to send
            bot: Bot instance for sending

        Returns:
            Result dict
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        return await send_reply_to_appeal(
            self.session,
            admin,
            appeal_id,
            message,
            bot
        )
