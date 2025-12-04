"""
InquiryRepository.

Repository for user inquiries (questions to admins).
"""

from datetime import UTC, datetime
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user_inquiry import InquiryMessage, InquiryStatus, UserInquiry
from app.repositories.base import BaseRepository


class InquiryRepository(BaseRepository[UserInquiry]):
    """Repository for UserInquiry model."""

    def __init__(self, session: AsyncSession):
        super().__init__(UserInquiry, session)

    async def get_new_inquiries(
        self,
        limit: int = 50,
    ) -> Sequence[UserInquiry]:
        """Get all new (unassigned) inquiries."""
        stmt = (
            select(UserInquiry)
            .where(UserInquiry.status == InquiryStatus.NEW.value)
            .options(selectinload(UserInquiry.user))
            .order_by(UserInquiry.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_admin_inquiries(
        self,
        admin_id: int,
        status: str | None = None,
    ) -> Sequence[UserInquiry]:
        """Get inquiries assigned to specific admin."""
        stmt = (
            select(UserInquiry)
            .where(UserInquiry.assigned_admin_id == admin_id)
            .options(selectinload(UserInquiry.user))
            .options(selectinload(UserInquiry.messages))
        )
        if status:
            stmt = stmt.where(UserInquiry.status == status)
        stmt = stmt.order_by(UserInquiry.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_user_active_inquiry(
        self,
        user_id: int,
    ) -> UserInquiry | None:
        """Get user's active inquiry (not closed)."""
        stmt = (
            select(UserInquiry)
            .where(UserInquiry.user_id == user_id)
            .where(UserInquiry.status != InquiryStatus.CLOSED.value)
            .options(selectinload(UserInquiry.messages))
            .options(selectinload(UserInquiry.assigned_admin))
            .order_by(UserInquiry.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_inquiries(
        self,
        user_id: int,
        limit: int = 10,
    ) -> Sequence[UserInquiry]:
        """Get user's inquiry history."""
        stmt = (
            select(UserInquiry)
            .where(UserInquiry.user_id == user_id)
            .options(selectinload(UserInquiry.messages))
            .order_by(UserInquiry.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def assign_to_admin(
        self,
        inquiry_id: int,
        admin_id: int,
    ) -> UserInquiry | None:
        """Assign inquiry to an admin."""
        stmt = (
            update(UserInquiry)
            .where(UserInquiry.id == inquiry_id)
            .where(UserInquiry.status == InquiryStatus.NEW.value)
            .values(
                assigned_admin_id=admin_id,
                status=InquiryStatus.IN_PROGRESS.value,
                assigned_at=datetime.now(UTC),
            )
            .returning(UserInquiry)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def close_inquiry(
        self,
        inquiry_id: int,
        closed_by: str,  # "user" or "admin"
    ) -> UserInquiry | None:
        """Close an inquiry."""
        stmt = (
            update(UserInquiry)
            .where(UserInquiry.id == inquiry_id)
            .values(
                status=InquiryStatus.CLOSED.value,
                closed_at=datetime.now(UTC),
                closed_by=closed_by,
            )
            .returning(UserInquiry)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_with_messages(
        self,
        inquiry_id: int,
    ) -> UserInquiry | None:
        """Get inquiry with all messages loaded."""
        stmt = (
            select(UserInquiry)
            .where(UserInquiry.id == inquiry_id)
            .options(selectinload(UserInquiry.messages))
            .options(selectinload(UserInquiry.user))
            .options(selectinload(UserInquiry.assigned_admin))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_new_inquiries(self) -> int:
        """Count new inquiries waiting for admin."""
        from sqlalchemy import func
        stmt = (
            select(func.count(UserInquiry.id))
            .where(UserInquiry.status == InquiryStatus.NEW.value)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class InquiryMessageRepository(BaseRepository[InquiryMessage]):
    """Repository for InquiryMessage model."""

    def __init__(self, session: AsyncSession):
        super().__init__(InquiryMessage, session)

    async def add_message(
        self,
        inquiry_id: int,
        sender_type: str,  # "user" or "admin"
        sender_id: int,
        message_text: str,
    ) -> InquiryMessage:
        """Add a message to an inquiry."""
        message = InquiryMessage(
            inquiry_id=inquiry_id,
            sender_type=sender_type,
            sender_id=sender_id,
            message_text=message_text,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_inquiry_messages(
        self,
        inquiry_id: int,
    ) -> Sequence[InquiryMessage]:
        """Get all messages for an inquiry."""
        stmt = (
            select(InquiryMessage)
            .where(InquiryMessage.inquiry_id == inquiry_id)
            .order_by(InquiryMessage.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
