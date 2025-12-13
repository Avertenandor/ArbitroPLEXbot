"""
Message templates for Bonus Search operations.

Contains messages for searching and viewing user bonuses.
"""

from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

# Separator line used throughout messages
SEPARATOR_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"


class BonusSearchMessages:
    """Message templates for bonus search operations."""

    @staticmethod
    def search_user_prompt() -> str:
        """
        Search user prompt.

        Returns:
            Search prompt message
        """
        return (
            "🔍 **Поиск бонусов пользователя**\n"
            f"{SEPARATOR_LINE}\n\n"
            "Введите @username или Telegram ID пользователя:"
        )

    @staticmethod
    def search_user_result(
        user,
        user_stats: dict,
        active_bonuses: list
    ) -> str:
        """
        Search user result.

        Args:
            user: User model instance
            user_stats: User bonus statistics dict
            active_bonuses: List of active bonuses (up to 5 shown)

        Returns:
            Search result message
        """
        safe_username = (
            escape_markdown(user.username)
            if user.username
            else str(user.telegram_id)
        )

        text = (
            f"👤 **Бонусы пользователя @{safe_username}**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"💰 Бонусный баланс: **"
            f"{format_usdt(user_stats['total_bonus_balance'])} USDT**\n"
            f"📈 Заработано ROI: **"
            f"{format_usdt(user_stats['total_bonus_roi_earned'])} USDT**\n"
            f"🟢 Активных: **"
            f"{user_stats['active_bonuses_count']}**\n"
            f"📋 Всего: **{user_stats['total_bonuses_count']}**\n\n"
        )

        if active_bonuses:
            text += "**Активные бонусы:**\n"
            for bonus in active_bonuses[:5]:
                progress = (
                    bonus.roi_progress_percent
                    if hasattr(bonus, "roi_progress_percent")
                    else 0
                )
                text += (
                    f"• ID `{bonus.id}`: "
                    f"{format_usdt(bonus.amount)} USDT "
                    f"(ROI: {progress:.0f}%)\n"
                )

        return text

    @staticmethod
    def user_not_found(user_input: str) -> str:
        """
        User not found error.

        Args:
            user_input: The input that failed to find user

        Returns:
            Error message
        """
        return (
            f"❌ **Пользователь не найден**\n\n"
            f"Не удалось найти: `{escape_markdown(user_input)}`\n\n"
            f"Попробуйте другой формат:\n"
            f"• @username\n"
            f"• Telegram ID (число)\n"
            f"• ID:42 (внутренний ID)"
        )
