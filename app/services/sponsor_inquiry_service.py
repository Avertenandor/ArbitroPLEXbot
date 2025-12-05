"""
Sponsor Inquiry Service.

Handles referral-to-sponsor communication logic.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sponsor_inquiry import (
    SponsorInquiry,
    SponsorInquiryMessage,
    SponsorInquiryStatus,
)
from app.models.user import User

if TYPE_CHECKING:
    from aiogram import Bot


class SponsorInquiryService:
    """Service for managing sponsor inquiries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session

    async def get_user_sponsor(self, user_id: int) -> User | None:
        """
        Get user's direct sponsor (level 1 referrer).

        Args:
            user_id: User ID

        Returns:
            Sponsor User object or None
        """
        from app.models.referral import Referral

        stmt = (
            select(User)
            .join(Referral, Referral.referrer_id == User.id)
            .where(
                Referral.referral_id == user_id,
                Referral.level == 1,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_inquiry(
        self,
        referral_id: int,
        referral_telegram_id: int,
        sponsor_id: int,
        sponsor_telegram_id: int,
        question: str,
    ) -> SponsorInquiry:
        """
        Create a new sponsor inquiry.

        Args:
            referral_id: ID of the user asking the question
            referral_telegram_id: Telegram ID of the referral
            sponsor_id: ID of the sponsor
            sponsor_telegram_id: Telegram ID of the sponsor
            question: The question text

        Returns:
            Created SponsorInquiry object
        """
        inquiry = SponsorInquiry(
            referral_id=referral_id,
            referral_telegram_id=referral_telegram_id,
            sponsor_id=sponsor_id,
            sponsor_telegram_id=sponsor_telegram_id,
            initial_question=question,
            status=SponsorInquiryStatus.NEW.value,
        )
        self.session.add(inquiry)
        await self.session.flush()

        # Create initial message
        message = SponsorInquiryMessage(
            inquiry_id=inquiry.id,
            sender_type="referral",
            message_text=question,
            is_read=False,
        )
        self.session.add(message)

        await self.session.commit()

        logger.info(
            f"Sponsor inquiry created: referral={referral_id}, "
            f"sponsor={sponsor_id}, inquiry_id={inquiry.id}"
        )

        return inquiry

    async def get_active_inquiry_for_referral(
        self, referral_id: int
    ) -> SponsorInquiry | None:
        """Get referral's active inquiry with their sponsor."""
        stmt = (
            select(SponsorInquiry)
            .options(
                selectinload(SponsorInquiry.messages),
                selectinload(SponsorInquiry.sponsor),
            )
            .where(
                SponsorInquiry.referral_id == referral_id,
                SponsorInquiry.status != SponsorInquiryStatus.CLOSED.value,
            )
            .order_by(SponsorInquiry.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_inquiries_for_sponsor(
        self, sponsor_id: int
    ) -> list[SponsorInquiry]:
        """Get all active inquiries where user is the sponsor."""
        stmt = (
            select(SponsorInquiry)
            .options(
                selectinload(SponsorInquiry.messages),
                selectinload(SponsorInquiry.referral),
            )
            .where(
                SponsorInquiry.sponsor_id == sponsor_id,
                SponsorInquiry.status != SponsorInquiryStatus.CLOSED.value,
            )
            .order_by(SponsorInquiry.last_message_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_unread_count_for_sponsor(self, sponsor_id: int) -> int:
        """Get count of unread inquiries for sponsor."""
        stmt = select(func.count(SponsorInquiry.id)).where(
            SponsorInquiry.sponsor_id == sponsor_id,
            SponsorInquiry.is_read_by_sponsor == False,  # noqa: E712
            SponsorInquiry.status != SponsorInquiryStatus.CLOSED.value,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_inquiry_by_id(
        self, inquiry_id: int
    ) -> SponsorInquiry | None:
        """Get inquiry by ID with all relations loaded."""
        stmt = (
            select(SponsorInquiry)
            .options(
                selectinload(SponsorInquiry.messages),
                selectinload(SponsorInquiry.referral),
                selectinload(SponsorInquiry.sponsor),
            )
            .where(SponsorInquiry.id == inquiry_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_message(
        self,
        inquiry_id: int,
        sender_type: str,  # 'referral' or 'sponsor'
        message_text: str,
    ) -> SponsorInquiryMessage | None:
        """
        Add a message to an inquiry.

        Args:
            inquiry_id: Inquiry ID
            sender_type: 'referral' or 'sponsor'
            message_text: Message content

        Returns:
            Created message or None if inquiry not found
        """
        inquiry = await self.get_inquiry_by_id(inquiry_id)
        if not inquiry:
            return None

        # Create message
        message = SponsorInquiryMessage(
            inquiry_id=inquiry_id,
            sender_type=sender_type,
            message_text=message_text,
            is_read=False,
        )
        self.session.add(message)

        # Update inquiry
        inquiry.last_message_at = datetime.now(UTC)

        # Update read status
        if sender_type == "referral":
            inquiry.is_read_by_sponsor = False
            inquiry.is_read_by_referral = True
        else:
            inquiry.is_read_by_referral = False
            inquiry.is_read_by_sponsor = True

        # Set status to in_progress if it was new
        if inquiry.status == SponsorInquiryStatus.NEW.value:
            inquiry.status = SponsorInquiryStatus.IN_PROGRESS.value

        self.session.add(inquiry)
        await self.session.commit()

        logger.debug(
            f"Message added to inquiry {inquiry_id} by {sender_type}"
        )

        return message

    async def mark_as_read_by_sponsor(self, inquiry_id: int) -> bool:
        """Mark inquiry as read by sponsor."""
        stmt = (
            update(SponsorInquiry)
            .where(SponsorInquiry.id == inquiry_id)
            .values(
                is_read_by_sponsor=True,
                status=SponsorInquiryStatus.IN_PROGRESS.value,
            )
        )
        result = await self.session.execute(stmt)

        # Mark all messages as read
        await self.session.execute(
            update(SponsorInquiryMessage)
            .where(
                SponsorInquiryMessage.inquiry_id == inquiry_id,
                SponsorInquiryMessage.sender_type == "referral",
            )
            .values(is_read=True)
        )

        await self.session.commit()
        return result.rowcount > 0

    async def mark_as_read_by_referral(self, inquiry_id: int) -> bool:
        """Mark inquiry as read by referral."""
        stmt = (
            update(SponsorInquiry)
            .where(SponsorInquiry.id == inquiry_id)
            .values(is_read_by_referral=True)
        )
        result = await self.session.execute(stmt)

        # Mark all messages as read
        await self.session.execute(
            update(SponsorInquiryMessage)
            .where(
                SponsorInquiryMessage.inquiry_id == inquiry_id,
                SponsorInquiryMessage.sender_type == "sponsor",
            )
            .values(is_read=True)
        )

        await self.session.commit()
        return result.rowcount > 0

    async def close_inquiry(
        self,
        inquiry_id: int,
        closed_by: str,  # 'referral' or 'sponsor'
    ) -> bool:
        """Close an inquiry."""
        stmt = (
            update(SponsorInquiry)
            .where(SponsorInquiry.id == inquiry_id)
            .values(
                status=SponsorInquiryStatus.CLOSED.value,
                closed_at=datetime.now(UTC),
                closed_by=closed_by,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()

        logger.info(f"Inquiry {inquiry_id} closed by {closed_by}")
        return result.rowcount > 0

    async def get_inquiry_history_for_referral(
        self, referral_id: int, limit: int = 10
    ) -> list[SponsorInquiry]:
        """Get inquiry history for referral."""
        stmt = (
            select(SponsorInquiry)
            .options(selectinload(SponsorInquiry.sponsor))
            .where(SponsorInquiry.referral_id == referral_id)
            .order_by(SponsorInquiry.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_inquiry_history_for_sponsor(
        self, sponsor_id: int, limit: int = 10
    ) -> list[SponsorInquiry]:
        """Get inquiry history for sponsor."""
        stmt = (
            select(SponsorInquiry)
            .options(selectinload(SponsorInquiry.referral))
            .where(SponsorInquiry.sponsor_id == sponsor_id)
            .order_by(SponsorInquiry.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


async def notify_sponsor_new_inquiry(
    bot: "Bot",
    sponsor_telegram_id: int,
    referral_username: str | None,
    referral_telegram_id: int,
    question_preview: str,
) -> bool:
    """
    Notify sponsor about new inquiry from referral.

    Args:
        bot: Telegram bot instance
        sponsor_telegram_id: Sponsor's Telegram ID
        referral_username: Referral's username
        referral_telegram_id: Referral's Telegram ID
        question_preview: First 100 chars of question

    Returns:
        True if notification sent successfully
    """
    try:
        user_display = (
            f"@{referral_username}" if referral_username
            else f"ID:{referral_telegram_id}"
        )

        # Escape markdown
        user_display = (
            user_display.replace("_", "\\_")
            .replace("*", "\\*")
            .replace("`", "\\`")
        )

        preview = question_preview[:100]
        if len(question_preview) > 100:
            preview += "..."

        text = (
            "💬 *Вопрос от вашего реферала!*\n\n"
            f"👤 От: {user_display}\n\n"
            f"📝 *Вопрос:*\n_{preview}_\n\n"
            "Нажмите «👥 Рефералы» → «📬 Входящие от рефералов» "
            "чтобы ответить."
        )

        await bot.send_message(
            sponsor_telegram_id,
            text,
            parse_mode="Markdown",
        )

        logger.info(
            f"Sponsor notification sent: sponsor={sponsor_telegram_id}, "
            f"referral={referral_telegram_id}"
        )
        return True

    except Exception as e:
        logger.warning(
            f"Failed to send sponsor notification: {e}",
            extra={
                "sponsor_telegram_id": sponsor_telegram_id,
                "referral_telegram_id": referral_telegram_id,
            },
        )
        return False


async def notify_referral_sponsor_reply(
    bot: "Bot",
    referral_telegram_id: int,
    sponsor_username: str | None,
    reply_preview: str,
) -> bool:
    """
    Notify referral about sponsor's reply.

    Args:
        bot: Telegram bot instance
        referral_telegram_id: Referral's Telegram ID
        sponsor_username: Sponsor's username
        reply_preview: First 100 chars of reply

    Returns:
        True if notification sent successfully
    """
    try:
        sponsor_display = (
            f"@{sponsor_username}" if sponsor_username
            else "Ваш спонсор"
        )

        # Escape markdown
        sponsor_display = (
            sponsor_display.replace("_", "\\_")
            .replace("*", "\\*")
            .replace("`", "\\`")
        )

        preview = reply_preview[:100]
        if len(reply_preview) > 100:
            preview += "..."

        text = (
            "💬 *Ответ от вашего спонсора!*\n\n"
            f"👤 От: {sponsor_display}\n\n"
            f"📝 *Сообщение:*\n_{preview}_\n\n"
            "Нажмите «👥 Рефералы» → «💬 Написать спонсору» "
            "чтобы продолжить диалог."
        )

        await bot.send_message(
            referral_telegram_id,
            text,
            parse_mode="Markdown",
        )

        logger.info(
            f"Referral notification sent: referral={referral_telegram_id}"
        )
        return True

    except Exception as e:
        logger.warning(
            f"Failed to send referral notification: {e}",
            extra={"referral_telegram_id": referral_telegram_id},
        )
        return False
