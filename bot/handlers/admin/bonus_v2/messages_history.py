"""
Message templates for Bonus History and Personal Bonuses.

Contains messages for displaying bonus history and admin's
personal bonus grants.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from bot.handlers.admin.bonus_v2.helpers import (
    get_bonus_status_emoji,
)
from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

if TYPE_CHECKING:
    from app.models.bonus_credit import BonusCredit

# Separator line used throughout messages
SEPARATOR_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"


class BonusHistoryMessages:
    """Message templates for bonus history and personal bonuses."""

    @staticmethod
    def bonus_history_header() -> str:
        """
        Bonus history header.

        Returns:
            Formatted history header
        """
        return (
            f"📋 **Последние 15 бонусов:**\n"
            f"{SEPARATOR_LINE}\n\n"
        )

    @staticmethod
    def bonus_history_item(
        bonus: "BonusCredit",
        status_emoji: str,
        progress: str = "",
    ) -> str:
        """
        Single bonus item in history list.

        Args:
            bonus: BonusCredit model instance
            status_emoji: Emoji representing bonus status
            progress: Optional progress string (e.g., " (45%)")

        Returns:
            Formatted bonus history item
        """
        admin_name = (
            bonus.admin.username if bonus.admin else "система"
        )
        user_name = (
            bonus.user.username
            if bonus.user
            else f"ID:{bonus.user_id}"
        )
        safe_user = (
            escape_markdown(user_name)
            if user_name
            else str(bonus.user_id)
        )
        safe_admin = (
            escape_markdown(admin_name)
            if admin_name
            else "система"
        )

        reason_short = (bonus.reason or "")[:25]
        if len(bonus.reason or "") > 25:
            reason_short += "..."

        return (
            f"{status_emoji} **{format_usdt(bonus.amount)}** → "
            f"@{safe_user}{progress}\n"
            f"   📝 _{reason_short}_ | 👤 @{safe_admin}\n"
            f"   🆔 `bonus:{bonus.id}` для просмотра деталей\n\n"
        )

    @staticmethod
    def bonus_history_footer() -> str:
        """
        Bonus history footer with instruction.

        Returns:
            Footer text
        """
        return "_Нажмите на ID чтобы увидеть детали бонуса_"

    @staticmethod
    def bonus_history_empty() -> str:
        """
        Empty bonus history message.

        Returns:
            Empty history message
        """
        return (
            "📋 **История бонусов пуста**\n\n"
            "Ещё не было начислено ни одного бонуса."
        )

    @staticmethod
    def my_bonuses(
        my_bonuses: list,
        total: Decimal,
        active_count: int
    ) -> str:
        """
        Admin's own bonuses display.

        Args:
            my_bonuses: List of bonus objects (up to 10)
            total: Total amount of all bonuses
            active_count: Number of active bonuses

        Returns:
            Formatted my bonuses message
        """
        text = (
            f"📑 **Ваши начисления**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"📊 Всего: **{len(my_bonuses)}** бонусов на "
            f"**{format_usdt(total)}** USDT\n"
            f"🟢 Активных: **{active_count}**\n\n"
        )

        for b in my_bonuses[:10]:
            status = get_bonus_status_emoji(b)
            user_name = (
                b.user.username
                if b.user
                else f"ID:{b.user_id}"
            )
            safe_user = escape_markdown(user_name)

            text += (
                f"{status} **{format_usdt(b.amount)}** → "
                f"@{safe_user}\n"
            )

        if len(my_bonuses) > 10:
            text += f"\n_...и ещё {len(my_bonuses) - 10} бонусов_"

        return text

    @staticmethod
    def my_bonuses_empty() -> str:
        """
        Empty my bonuses message.

        Returns:
            Empty message
        """
        return (
            "📑 **Ваши начисления**\n\n"
            "Вы ещё не начислили ни одного бонуса."
        )
