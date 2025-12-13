"""
User Activity Service - Analytics Module.

Methods for analyzing user activities and generating statistics.
"""

from datetime import datetime
from typing import Any

from loguru import logger

from app.models.user_activity import ActivityType


class UserActivityAnalyticsMixin:
    """Mixin with analytics and reporting methods."""

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
                "message": (
                    a.message_text[:100] if a.message_text else None
                ),
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
            stats = {
                "activities": {},
                "total_actions": 0,
                "total_unique_users": 0,
            }

        try:
            funnel = await self.repo.get_funnel_stats(hours)
        except Exception as e:
            logger.warning(f"Failed to get funnel stats: {e}")
            funnel = {
                "starts": 0,
                "wallets_entered": 0,
                "plex_paid": 0,
                "first_deposits": 0,
            }

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
                if starts > 0
                else 0
            ),
            "wallet_to_plex": (
                round(
                    funnel["plex_paid"]
                    / funnel["wallets_entered"]
                    * 100,
                    1,
                )
                if funnel["wallets_entered"] > 0
                else 0
            ),
            "plex_to_deposit": (
                round(
                    funnel["first_deposits"] / funnel["plex_paid"] * 100,
                    1,
                )
                if funnel["plex_paid"] > 0
                else 0
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
        wallet_conv = conv["start_to_wallet"]
        text += (
            f"• Ввели кошелёк: "
            f"**{funnel['wallets_entered']}** ({wallet_conv}%)\n"
        )
        plex_conv = conv["wallet_to_plex"]
        text += (
            f"• Оплатили PLEX: "
            f"**{funnel['plex_paid']}** ({plex_conv}%)\n"
        )
        deposit_conv = conv["plex_to_deposit"]
        text += (
            f"• Сделали депозит: "
            f"**{funnel['first_deposits']}** ({deposit_conv}%)\n\n"
        )

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
                result.append(
                    {
                        "telegram_id": a.telegram_id,
                        "user_id": a.user_id,
                        "time": a.created_at.strftime("%Y-%m-%d %H:%M"),
                        "description": a.description,
                    }
                )

        return result
