"""
InquiryService.

Business logic for user inquiries (questions to admins).
"""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_inquiry import InquiryStatus, UserInquiry
from app.repositories.inquiry_repository import (
    InquiryMessageRepository,
    InquiryRepository,
)


class InquiryService:
    """Service for managing user inquiries."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.inquiry_repo = InquiryRepository(session)
        self.message_repo = InquiryMessageRepository(session)

    async def create_inquiry(
        self,
        user_id: int,
        telegram_id: int,
        question_text: str,
    ) -> UserInquiry:
        """
        Create a new inquiry from user.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID
            question_text: The question text

        Returns:
            Created UserInquiry
        """
        inquiry = UserInquiry(
            user_id=user_id,
            telegram_id=telegram_id,
            initial_question=question_text,
            status=InquiryStatus.NEW.value,
            created_at=datetime.now(UTC),
        )
        self.session.add(inquiry)
        await self.session.commit()
        await self.session.refresh(inquiry)

        logger.info(
            f"Created inquiry #{inquiry.id} from user {user_id}: "
            f"{question_text[:50]}..."
        )
        return inquiry

    async def get_user_active_inquiry(
        self,
        user_id: int,
    ) -> UserInquiry | None:
        """Get user's active (not closed) inquiry."""
        return await self.inquiry_repo.get_user_active_inquiry(user_id)

    async def get_new_inquiries(self) -> list[UserInquiry]:
        """Get all new inquiries waiting for admin."""
        inquiries = await self.inquiry_repo.get_new_inquiries()
        return list(inquiries)

    async def get_admin_inquiries(
        self,
        admin_id: int,
        status: str | None = None,
    ) -> list[UserInquiry]:
        """Get inquiries assigned to specific admin."""
        inquiries = await self.inquiry_repo.get_admin_inquiries(
            admin_id, status
        )
        return list(inquiries)

    async def assign_to_admin(
        self,
        inquiry_id: int,
        admin_id: int,
    ) -> UserInquiry | None:
        """
        Assign inquiry to an admin.

        Returns None if inquiry already taken or doesn't exist.
        """
        inquiry = await self.inquiry_repo.assign_to_admin(inquiry_id, admin_id)
        if inquiry:
            logger.info(
                f"Inquiry #{inquiry_id} assigned to admin {admin_id}"
            )
        return inquiry

    async def add_user_message(
        self,
        inquiry_id: int,
        user_id: int,
        message_text: str,
    ) -> None:
        """Add a message from user to inquiry."""
        await self.message_repo.add_message(
            inquiry_id=inquiry_id,
            sender_type="user",
            sender_id=user_id,
            message_text=message_text,
        )
        logger.debug(f"User {user_id} sent message to inquiry #{inquiry_id}")

    async def add_admin_message(
        self,
        inquiry_id: int,
        admin_id: int,
        message_text: str,
    ) -> None:
        """Add a message from admin to inquiry."""
        await self.message_repo.add_message(
            inquiry_id=inquiry_id,
            sender_type="admin",
            sender_id=admin_id,
            message_text=message_text,
        )
        logger.debug(f"Admin {admin_id} sent message to inquiry #{inquiry_id}")

    async def close_inquiry(
        self,
        inquiry_id: int,
        closed_by: str,  # "user" or "admin"
    ) -> UserInquiry | None:
        """Close an inquiry."""
        inquiry = await self.inquiry_repo.close_inquiry(inquiry_id, closed_by)
        if inquiry:
            logger.info(
                f"Inquiry #{inquiry_id} closed by {closed_by}"
            )
        return inquiry

    async def get_inquiry_with_messages(
        self,
        inquiry_id: int,
    ) -> UserInquiry | None:
        """Get inquiry with all messages."""
        return await self.inquiry_repo.get_with_messages(inquiry_id)

    async def count_new_inquiries(self) -> int:
        """Count new inquiries waiting for admin."""
        return await self.inquiry_repo.count_new_inquiries()

    async def get_inquiry_by_id(
        self,
        inquiry_id: int,
    ) -> UserInquiry | None:
        """Get inquiry by ID."""
        return await self.inquiry_repo.get_by_id(inquiry_id)
