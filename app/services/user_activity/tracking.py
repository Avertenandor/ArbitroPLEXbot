"""
User Activity Service - Tracking Module.

Methods for tracking various user activities.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from app.models.user_activity import ActivityType, UserActivity


class UserActivityTrackingMixin:
    """Mixin with activity tracking methods."""

    async def log_start(
        self,
        telegram_id: int,
        user_id: int | None = None,
        referral_code: str | None = None,
        username: str | None = None,
    ) -> UserActivity:
        """Log /start command."""
        activity_type = (
            ActivityType.START_REFERRAL
            if referral_code
            else ActivityType.START
        )
        description = "Started bot"
        if referral_code:
            description += f" via referral {referral_code}"

        return await self.log(
            telegram_id=telegram_id,
            activity_type=activity_type,
            user_id=user_id,
            description=description,
            extra_data={
                "referral_code": referral_code,
                "username": username,
            },
        )

    async def log_wallet_entered(
        self,
        telegram_id: int,
        user_id: int | None = None,
        wallet_address: str | None = None,
    ) -> UserActivity:
        """Log wallet address entry."""
        description = "Entered wallet"
        if wallet_address:
            description = f"Entered wallet: {wallet_address[:10]}..."

        return await self.log(
            telegram_id=telegram_id,
            activity_type=ActivityType.WALLET_ENTERED,
            user_id=user_id,
            description=description,
            extra_data={
                "wallet_short": (
                    wallet_address[:10] if wallet_address else None
                ),
            },
        )

    async def log_plex_paid(
        self,
        telegram_id: int,
        user_id: int | None = None,
        amount: float = 10.0,
    ) -> UserActivity:
        """Log PLEX payment for entry."""
        return await self.log(
            telegram_id=telegram_id,
            activity_type=ActivityType.PLEX_PAID,
            user_id=user_id,
            description=f"Paid {amount} PLEX for entry",
            extra_data={"amount": amount},
        )

    async def log_deposit(
        self,
        telegram_id: int,
        user_id: int,
        amount: float,
        level: int,
        is_confirmed: bool = True,
    ) -> UserActivity:
        """Log deposit event."""
        activity_type = (
            ActivityType.DEPOSIT_CONFIRMED
            if is_confirmed
            else ActivityType.DEPOSIT_STARTED
        )
        return await self.log(
            telegram_id=telegram_id,
            activity_type=activity_type,
            user_id=user_id,
            description=f"Deposit ${amount:.2f} level {level}",
            extra_data={
                "amount": amount,
                "level": level,
                "confirmed": is_confirmed,
            },
        )

    async def log_withdrawal(
        self,
        telegram_id: int,
        user_id: int,
        amount: float,
        is_completed: bool = False,
    ) -> UserActivity:
        """Log withdrawal event."""
        activity_type = (
            ActivityType.WITHDRAWAL_COMPLETED
            if is_completed
            else ActivityType.WITHDRAWAL_REQUESTED
        )
        return await self.log(
            telegram_id=telegram_id,
            activity_type=activity_type,
            user_id=user_id,
            description=f"Withdrawal ${amount:.2f}",
            extra_data={"amount": amount, "completed": is_completed},
        )

    async def log_message(
        self,
        telegram_id: int,
        user_id: int | None = None,
        message_text: str | None = None,
        is_button: bool = False,
    ) -> UserActivity:
        """Log any message or button click."""
        activity_type = (
            ActivityType.BUTTON_CLICKED
            if is_button
            else ActivityType.MESSAGE_SENT
        )
        description = None
        if message_text:
            prefix = "Button" if is_button else "Message"
            description = f"{prefix}: {message_text[:50]}..."

        return await self.log(
            telegram_id=telegram_id,
            activity_type=activity_type,
            user_id=user_id,
            message_text=message_text,
            description=description,
        )

    async def log_support(
        self,
        telegram_id: int,
        user_id: int,
        inquiry_text: str | None = None,
    ) -> UserActivity:
        """Log support request."""
        return await self.log(
            telegram_id=telegram_id,
            activity_type=ActivityType.SUPPORT_REQUEST,
            user_id=user_id,
            message_text=inquiry_text,
            description="Opened support request",
        )

    async def log_ai_interaction(
        self,
        telegram_id: int,
        user_id: int | None = None,
        question: str | None = None,
        is_response: bool = False,
    ) -> UserActivity:
        """Log AI assistant interaction."""
        activity_type = (
            ActivityType.AI_RESPONSE
            if is_response
            else ActivityType.AI_QUESTION
        )
        return await self.log(
            telegram_id=telegram_id,
            activity_type=activity_type,
            user_id=user_id,
            message_text=question,
            description="AI interaction",
        )

    async def log_error(
        self,
        telegram_id: int,
        user_id: int | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> UserActivity:
        """Log error occurrence."""
        return await self.log(
            telegram_id=telegram_id,
            activity_type=ActivityType.ERROR_OCCURRED,
            user_id=user_id,
            description=f"Error: {error_type}",
            extra_data={
                "error_type": error_type,
                "error_message": error_message,
            },
        )

    async def log_ai_conversation(
        self,
        telegram_id: int,
        admin_name: str,
        question: str,
        answer: str,
    ) -> UserActivity:
        """
        Log AI assistant conversation (question + answer).

        Args:
            telegram_id: Admin's Telegram ID
            admin_name: Admin display name
            question: User's question
            answer: AI's response

        Returns:
            Created activity record
        """
        return await self.log(
            telegram_id=telegram_id,
            activity_type=ActivityType.AI_QUESTION,
            description=f"AI разговор с {admin_name}",
            message_text=question[:500] if question else None,
            extra_data={
                "admin_name": admin_name,
                "question": question[:1000] if question else None,
                "answer": answer[:2000] if answer else None,
            },
        )

    async def log_ai_conversation_safe(
        self,
        telegram_id: int,
        admin_name: str,
        question: str,
        answer: str,
    ) -> UserActivity | None:
        """
        Safely log AI conversation without breaking main flow.
        Non-blocking - returns None on any error.
        """
        try:
            return await self.log_ai_conversation(
                telegram_id=telegram_id,
                admin_name=admin_name,
                question=question,
                answer=answer,
            )
        except Exception as e:
            logger.debug(f"AI conversation logging skipped: {e}")
            return None

    async def get_ai_conversations(
        self,
        hours: int = 24,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get recent AI conversations.

        Args:
            hours: Lookback period
            limit: Max conversations

        Returns:
            List of conversations with admin name, question, answer
        """
        since = datetime.now(UTC) - timedelta(hours=hours)
        activities = await self.repo.get_user_activities(
            activity_type=ActivityType.AI_QUESTION,
            since=since,
            limit=limit,
        )

        conversations = []
        for a in activities:
            extra_data = a.extra_data or {}
            conversations.append(
                {
                    "time": a.created_at.strftime("%Y-%m-%d %H:%M"),
                    "admin_name": extra_data.get(
                        "admin_name", "Unknown"
                    ),
                    "telegram_id": a.telegram_id,
                    "question": extra_data.get(
                        "question", a.message_text or ""
                    ),
                    "answer": extra_data.get("answer", "")[:500],
                }
            )

        return conversations

    async def format_ai_conversations_for_aria(
        self,
        hours: int = 24,
    ) -> str:
        """
        Format AI conversations for ARIA to summarize.

        Args:
            hours: Lookback period

        Returns:
            Formatted string of conversations
        """
        conversations = await self.get_ai_conversations(hours, limit=30)

        if not conversations:
            return f"За последние {hours}ч разговоров с AI не было."

        text = f"📝 **Разговоры с AI за {hours}ч:**\n\n"

        for conv in conversations:
            question_preview = conv["question"][:100]
            if len(conv["question"]) > 100:
                question_preview += "..."

            text += (
                f"⏰ {conv['time']} — **{conv['admin_name']}**\n"
                f"❓ {question_preview}\n\n"
            )

        text += f"Всего разговоров: {len(conversations)}"
        return text
