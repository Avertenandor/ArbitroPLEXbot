"""
User Activity Service.

Business logic for tracking and analyzing user activities.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_activity import ActivityType, UserActivity
from app.repositories.user_activity_repository import UserActivityRepository


class UserActivityService:
    """Service for tracking and analyzing user activities."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service."""
        self.session = session
        self.repo = UserActivityRepository(session)

    # ============ CONFIGURATION ============

    # Maximum records to keep (older will be deleted)
    MAX_RECORDS = 100000

    # Days to keep records
    RETENTION_DAYS = 30

    # ============ LOGGING METHODS ============

    async def log_safe(
        self,
        telegram_id: int,
        activity_type: str,
        user_id: int | None = None,
        description: str | None = None,
        message_text: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> UserActivity | None:
        """
        Safely log activity without raising exceptions.
        Use this for non-critical logging that should not break the main flow.

        Returns:
            Created activity record or None on error
        """
        try:
            return await self.log(
                telegram_id=telegram_id,
                activity_type=activity_type,
                user_id=user_id,
                description=description,
                message_text=message_text,
                extra_data=extra_data,
            )
        except Exception as e:
            # Log but don't raise - non-blocking
            logger.debug(f"Activity logging skipped: {e}")
            return None

    async def log(
        self,
        telegram_id: int,
        activity_type: str,
        user_id: int | None = None,
        description: str | None = None,
        message_text: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> UserActivity:
        """
        Log any user activity.

        Args:
            telegram_id: User's Telegram ID
            activity_type: Type from ActivityType
            user_id: Internal user ID if known
            description: Human-readable description
            message_text: Full message text
            extra_data: Additional JSON data

        Returns:
            Created activity record
        """
        try:
            activity = await self.repo.log_activity(
                telegram_id=telegram_id,
                activity_type=activity_type,
                user_id=user_id,
                description=description,
                message_text=message_text,
                extra_data=extra_data,
            )
            return activity
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            raise

    async def log_start(
        self,
        telegram_id: int,
        user_id: int | None = None,
        referral_code: str | None = None,
        username: str | None = None,
    ) -> UserActivity:
        """Log /start command."""
        activity_type = (
            ActivityType.START_REFERRAL if referral_code else ActivityType.START
        )
        return await self.log(
            telegram_id=telegram_id,
            activity_type=activity_type,
            user_id=user_id,
            description="Started bot" + (f" via referral {referral_code}" if referral_code else ""),
            extra_data={"referral_code": referral_code, "username": username},
        )

    async def log_wallet_entered(
        self,
        telegram_id: int,
        user_id: int | None = None,
        wallet_address: str | None = None,
    ) -> UserActivity:
        """Log wallet address entry."""
        return await self.log(
            telegram_id=telegram_id,
            activity_type=ActivityType.WALLET_ENTERED,
            user_id=user_id,
            description=f"Entered wallet: {wallet_address[:10]}..." if wallet_address else "Entered wallet",
            extra_data={"wallet_short": wallet_address[:10] if wallet_address else None},
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
            ActivityType.DEPOSIT_CONFIRMED if is_confirmed
            else ActivityType.DEPOSIT_STARTED
        )
        return await self.log(
            telegram_id=telegram_id,
            activity_type=activity_type,
            user_id=user_id,
            description=f"Deposit ${amount:.2f} level {level}",
            extra_data={"amount": amount, "level": level, "confirmed": is_confirmed},
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
            ActivityType.WITHDRAWAL_COMPLETED if is_completed
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
            ActivityType.BUTTON_CLICKED if is_button
            else ActivityType.MESSAGE_SENT
        )
        return await self.log(
            telegram_id=telegram_id,
            activity_type=activity_type,
            user_id=user_id,
            message_text=message_text,
            description=f"{'Button' if is_button else 'Message'}: {message_text[:50]}..." if message_text else None,
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
            ActivityType.AI_RESPONSE if is_response
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
            extra_data={"error_type": error_type, "error_message": error_message},
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
            conversations.append({
                "time": a.created_at.strftime("%Y-%m-%d %H:%M"),
                "admin_name": extra_data.get("admin_name", "Unknown"),
                "telegram_id": a.telegram_id,
                "question": extra_data.get("question", a.message_text or ""),
                "answer": extra_data.get("answer", "")[:500],
            })

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

    # ============ ANALYTICS METHODS ============

    async def get_user_journey(
        self,
        telegram_id: int,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get complete user journey as formatted list.

        Args:
            telegram_id: User's Telegram ID
            limit: Max activities

        Returns:
            List of formatted activity dicts
        """
        activities = await self.repo.get_user_journey(telegram_id, limit)
        return [
            {
                "time": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "type": a.activity_type,
                "emoji": a.type_emoji,
                "description": a.description,
                "message": a.message_text[:100] if a.message_text else None,
            }
            for a in activities
        ]

    async def get_comprehensive_stats(
        self,
        hours: int = 24,
    ) -> dict[str, Any]:
        """
        Get comprehensive activity statistics for ARIA.

        Args:
            hours: Lookback period

        Returns:
            Complete statistics dict
        """
        # Get stats with error handling for each query
        try:
            stats = await self.repo.get_activity_stats(hours)
        except Exception as e:
            logger.warning(f"Failed to get activity stats: {e}")
            stats = {"activities": {}, "total_actions": 0, "total_unique_users": 0}

        try:
            funnel = await self.repo.get_funnel_stats(hours)
        except Exception as e:
            logger.warning(f"Failed to get funnel stats: {e}")
            funnel = {"starts": 0, "wallets_entered": 0, "plex_paid": 0, "first_deposits": 0}

        try:
            hourly = await self.repo.get_hourly_activity(hours)
        except Exception as e:
            logger.warning(f"Failed to get hourly activity: {e}")
            hourly = []

        # Calculate conversion rates
        starts = funnel.get("starts", 0)
        conversions = {
            "start_to_wallet": (
                round(funnel["wallets_entered"] / starts * 100, 1)
                if starts > 0 else 0
            ),
            "wallet_to_plex": (
                round(funnel["plex_paid"] / funnel["wallets_entered"] * 100, 1)
                if funnel["wallets_entered"] > 0 else 0
            ),
            "plex_to_deposit": (
                round(funnel["first_deposits"] / funnel["plex_paid"] * 100, 1)
                if funnel["plex_paid"] > 0 else 0
            ),
        }

        return {
            "period_hours": hours,
            "funnel": funnel,
            "conversions": conversions,
            "activity_by_type": stats.get("activities", {}),
            "total_actions": stats.get("total_actions", 0),
            "unique_users": stats.get("total_unique_users", 0),
            "hourly": hourly,
        }

    async def format_stats_for_aria(
        self,
        hours: int = 24,
    ) -> str:
        """
        Format statistics as text for ARIA assistant.

        Args:
            hours: Lookback period

        Returns:
            Formatted statistics string
        """
        stats = await self.get_comprehensive_stats(hours)
        funnel = stats["funnel"]
        conv = stats["conversions"]
        activities = stats["activity_by_type"]

        text = f"📊 **Статистика активности за {hours}ч:**\n\n"

        # Funnel
        text += "**🔄 Воронка регистрации:**\n"
        text += f"• Нажали /start: **{funnel['starts']}**\n"
        text += f"• Ввели кошелёк: **{funnel['wallets_entered']}** ({conv['start_to_wallet']}%)\n"
        text += f"• Оплатили PLEX: **{funnel['plex_paid']}** ({conv['wallet_to_plex']}%)\n"
        text += f"• Сделали депозит: **{funnel['first_deposits']}** ({conv['plex_to_deposit']}%)\n\n"

        # Key activities
        text += "**📝 Ключевые действия:**\n"
        key_types = [
            (ActivityType.MESSAGE_SENT, "Сообщений"),
            (ActivityType.BUTTON_CLICKED, "Нажатий кнопок"),
            (ActivityType.SUPPORT_REQUEST, "Обращений в поддержку"),
            (ActivityType.AI_QUESTION, "Вопросов к AI"),
            (ActivityType.ERROR_OCCURRED, "Ошибок"),
        ]
        for atype, label in key_types:
            if atype in activities:
                count = activities[atype]["count"]
                users = activities[atype]["unique_users"]
                text += f"• {label}: **{count}** ({users} юзеров)\n"

        text += f"\n**Всего действий:** {stats['total_actions']}\n"
        text += f"**Уникальных пользователей:** {stats['unique_users']}\n"

        return text

    async def search_user_by_action(
        self,
        activity_type: str,
        since: datetime | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Find users who performed specific action.

        Args:
            activity_type: Type of activity to search
            since: Start date
            limit: Max results

        Returns:
            List of users with their activity
        """
        activities = await self.repo.get_user_activities(
            activity_type=activity_type,
            since=since,
            limit=limit,
        )

        result = []
        seen_users = set()
        for a in activities:
            if a.telegram_id not in seen_users:
                seen_users.add(a.telegram_id)
                result.append({
                    "telegram_id": a.telegram_id,
                    "user_id": a.user_id,
                    "time": a.created_at.strftime("%Y-%m-%d %H:%M"),
                    "description": a.description,
                })

        return result

    # ============ MAINTENANCE METHODS ============

    async def cleanup_old_records(self) -> int:
        """
        Delete records older than RETENTION_DAYS.

        Returns:
            Number of deleted records
        """
        try:
            cutoff = datetime.now(UTC) - timedelta(days=self.RETENTION_DAYS)
            result = await self.session.execute(
                text(
                    "DELETE FROM user_activities WHERE created_at < :cutoff"
                ),
                {"cutoff": cutoff},
            )
            deleted = result.rowcount or 0
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old activity records")
            return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return 0

    async def enforce_max_records(self) -> int:
        """
        Delete oldest records if total exceeds MAX_RECORDS.

        Returns:
            Number of deleted records
        """
        try:
            # Count total records
            count_result = await self.session.execute(
                text("SELECT COUNT(*) FROM user_activities")
            )
            total = count_result.scalar() or 0

            if total <= self.MAX_RECORDS:
                return 0

            # Delete oldest records
            to_delete = total - self.MAX_RECORDS
            result = await self.session.execute(
                text("""
                    DELETE FROM user_activities
                    WHERE id IN (
                        SELECT id FROM user_activities
                        ORDER BY created_at ASC
                        LIMIT :limit
                    )
                """),
                {"limit": to_delete},
            )
            deleted = result.rowcount or 0
            if deleted > 0:
                logger.info(
                    f"Enforced max records limit: deleted {deleted} oldest records"
                )
            return deleted
        except Exception as e:
            logger.error(f"Failed to enforce max records: {e}")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """
        Get activity logging statistics.

        Returns:
            Dict with stats: total, oldest, newest, by_type
        """
        try:
            # Total count
            count_result = await self.session.execute(
                text("SELECT COUNT(*) FROM user_activities")
            )
            total = count_result.scalar() or 0

            # Oldest and newest
            range_result = await self.session.execute(
                text("""
                    SELECT MIN(created_at), MAX(created_at)
                    FROM user_activities
                """)
            )
            row = range_result.fetchone()
            oldest = row[0] if row else None
            newest = row[1] if row else None

            # By type
            type_result = await self.session.execute(
                text("""
                    SELECT activity_type, COUNT(*) as cnt
                    FROM user_activities
                    GROUP BY activity_type
                    ORDER BY cnt DESC
                """)
            )
            by_type = {row[0]: row[1] for row in type_result.fetchall()}

            return {
                "total": total,
                "max_records": self.MAX_RECORDS,
                "retention_days": self.RETENTION_DAYS,
                "oldest": oldest.isoformat() if oldest else None,
                "newest": newest.isoformat() if newest else None,
                "by_type": by_type,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
