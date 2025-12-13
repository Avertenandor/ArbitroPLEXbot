"""
AI User Inquiries Service.

Provides user inquiry management tools for AI assistant with STRICT security:
- Only callable from admin AI assistant context
- Validates admin credentials before every operation
- Full audit logging

SECURITY: This service is ONLY accessible through the AI assistant
when a verified admin is in an authenticated admin session.
"""
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_inquiry import InquiryStatus
from app.services.ai.commons import verify_admin
from app.services.ai_inquiries_formatter import (
    format_admin_name,
    format_inquiry_details,
    format_inquiry_list_item,
    format_inquiry_reply,
    format_text_preview,
    format_user_info,
)
from app.services.ai_inquiries_repository import (
    get_inquiries_counts,
    get_inquiries_with_filter,
    get_inquiry_by_id,
    validate_inquiry_assignment,
    validate_inquiry_status,
    validate_message,
    validate_status,
)
from app.services.ai_inquiries_operations import (
    assign_inquiry_to_admin,
    auto_assign_if_needed,
    close_inquiry_with_reason,
    create_admin_message,
    log_inquiry_action,
    send_message_to_user,
)
from app.services.ai_inquiries_responses import (
    close_inquiry_response,
    empty_inquiries_response,
    error_response,
    inquiries_list_response,
    inquiry_details_response,
    reply_inquiry_response,
    take_inquiry_response,
)

class AIInquiriesService:
    """
    AI-powered user inquiries management service.

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
        self.admin_username = ( self.admin_data.get("username") or self.admin_data.get("Имя")
        )

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials from session data."""
        return await verify_admin(self.session, self.admin_telegram_id)

    async def get_inquiries_list(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get list of inquiries with optional status filter."""
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return error_response(error)

        # Validate status
        is_valid, error_msg = validate_status(status)
        if not is_valid:
            return error_response(error_msg)

        # Get inquiries from repository
        inquiries = await get_inquiries_with_filter(
            self.session,
            status,
            limit
        )

        if not inquiries:
            return empty_inquiries_response(status)

        # Format inquiries
        inquiries_list = [
            format_inquiry_list_item(inq)
            for inq in inquiries
        ]

        # Get counts by status
        counts = await get_inquiries_counts(self.session)

        return inquiries_list_response(inquiries_list, counts)

    async def get_inquiry_details(
        self,
        inquiry_id: int,
    ) -> dict[str, Any]:
        """Get detailed information about inquiry with messages."""
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return error_response(error)

        # Get inquiry from repository
        inquiry = await get_inquiry_by_id(
            self.session,
            inquiry_id,
            with_messages=True
        )

        if not inquiry:
            return error_response(f"❌ Обращение ID {inquiry_id} не найдено")

        # Format inquiry details
        inquiry_data = format_inquiry_details(inquiry)

        return inquiry_details_response(inquiry_data, inquiry_id)

    async def take_inquiry(
        self,
        inquiry_id: int,
    ) -> dict[str, Any]:
        """Take inquiry for processing (assign to current admin)."""
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return error_response(error)

        # Get inquiry from repository
        inquiry = await get_inquiry_by_id(self.session, inquiry_id)

        # Validate inquiry
        is_valid, error_msg = validate_inquiry_status(inquiry, inquiry_id)
        if not is_valid:
            return error_response(error_msg)

        # Validate assignment
        is_valid, error_msg = validate_inquiry_assignment(inquiry, admin.id)
        if not is_valid:
            return error_response(error_msg)

        # Assign to admin
        await assign_inquiry_to_admin(self.session, inquiry, admin)

        # Format response data
        user_info = format_user_info(inquiry.user)
        admin_name = format_admin_name(admin)
        question = format_text_preview(inquiry.initial_question, 100)

        # Log action
        log_inquiry_action("took", admin.telegram_id, inquiry_id, user_info)

        return take_inquiry_response(
            inquiry_id,
            user_info,
            question,
            admin_name
        )

    async def reply_to_inquiry(
        self,
        inquiry_id: int,
        message: str,
        bot: Any = None,
    ) -> dict[str, Any]:
        """Send reply to user's inquiry."""
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return error_response(error)
        if not bot:
            return error_response("❌ Бот не инициализирован")

        # Validate message
        is_valid, error_msg = validate_message(message)
        if not is_valid:
            return error_response(error_msg)

        # Get inquiry from repository
        inquiry = await get_inquiry_by_id(self.session, inquiry_id)

        # Validate inquiry
        is_valid, error_msg = validate_inquiry_status(inquiry, inquiry_id)
        if not is_valid:
            return error_response(error_msg)

        # Auto-assign if not assigned
        await auto_assign_if_needed(self.session, inquiry, admin)

        # Create message record
        await create_admin_message(self.session, inquiry_id, admin, message)
        await self.session.commit()

        # Send message to user
        admin_name = format_admin_name(admin)
        formatted_msg = format_inquiry_reply(message, admin_name)
        success, error = await send_message_to_user(
            bot,
            inquiry.telegram_id,
            formatted_msg
        )
        if not success:
            return error_response(error)

        # Format response data
        user_info = format_user_info(inquiry.user)
        msg_preview = format_text_preview(message, 100)

        # Log action
        log_inquiry_action(
            "replied to",
            admin.telegram_id,
            inquiry_id,
            format_text_preview(message, 50)
        )

        return reply_inquiry_response(inquiry_id, user_info, msg_preview)

    async def close_inquiry(
        self,
        inquiry_id: int,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Close an inquiry with optional reason."""
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return error_response(error)

        # Get inquiry from repository
        inquiry = await get_inquiry_by_id(self.session, inquiry_id)

        # Validate inquiry exists
        if not inquiry:
            return error_response(f"❌ Обращение ID {inquiry_id} не найдено")
        if inquiry.status == InquiryStatus.CLOSED:
            return error_response("❌ Обращение уже закрыто")

        # Close inquiry
        await close_inquiry_with_reason(self.session, inquiry, admin, reason)

        # Format response data
        user_info = format_user_info(inquiry.user)
        admin_name = format_admin_name(admin)

        # Log action
        log_inquiry_action(
            "closed",
            admin.telegram_id,
            inquiry_id,
            reason or "no reason"
        )

        return close_inquiry_response(
            inquiry_id,
            user_info,
            admin_name,
            reason
        )
