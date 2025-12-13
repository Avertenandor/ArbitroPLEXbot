"""
Message templates for Bonus Viewing and Cancellation operations.

Contains messages for cancelling bonuses and viewing bonus details.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

if TYPE_CHECKING:
    from app.models.bonus_credit import BonusCredit

# Separator line used throughout messages
SEPARATOR_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"


class BonusViewMessages:
    """Message templates for bonus viewing and cancellation."""

    @staticmethod
    def cancel_bonus_list_header() -> str:
        """
        Cancel bonus list header.

        Returns:
            Cancel list header
        """
        return (
            f"⚠️ **Отмена бонусов**\n{SEPARATOR_LINE}\n\n"
            f"**Активные бонусы:**\n\n"
        )

    @staticmethod
    def cancel_bonus_item(
        bonus: "BonusCredit",
        progress: float
    ) -> str:
        """
        Cancel bonus list item.

        Args:
            bonus: BonusCredit model instance
            progress: ROI progress percentage

        Returns:
            Cancel list item
        """
        user_name = (
            bonus.user.username
            if bonus.user
            else f"ID:{bonus.user_id}"
        )
        safe_user = escape_markdown(user_name)

        reason_short = (bonus.reason or "")[:20]
        if len(bonus.reason or "") > 20:
            reason_short += "..."

        return (
            f"🟢 **ID {bonus.id}:** "
            f"{format_usdt(bonus.amount)} USDT → @{safe_user}\n"
            f"   ROI: {progress:.0f}% | _{reason_short}_\n\n"
        )

    @staticmethod
    def cancel_bonus_list_footer() -> str:
        """
        Cancel bonus list footer.

        Returns:
            Footer text
        """
        return "\n⚠️ _Выберите бонус для отмены:_"

    @staticmethod
    def cancel_confirm(
        bonus_id: int,
        user_name: str,
        amount: Decimal,
        reason: str
    ) -> str:
        """
        Cancel bonus confirmation prompt.

        Args:
            bonus_id: Bonus ID to cancel
            user_name: Username of bonus recipient
            amount: Bonus amount
            reason: Original grant reason

        Returns:
            Cancel confirmation message
        """
        safe_user = escape_markdown(user_name)
        safe_reason = escape_markdown(reason or "не указана")

        return (
            f"⚠️ **Отмена бонуса #{bonus_id}**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"👤 Получатель: @{safe_user}\n"
            f"💰 Сумма: **{format_usdt(amount)} USDT**\n"
            f"📝 Причина начисления: _{safe_reason}_\n\n"
            f"⚠️ **Введите причину отмены:**"
        )

    @staticmethod
    def cancel_success(
        bonus_id: int,
        cancel_reason: str,
        admin_username: str
    ) -> str:
        """
        Bonus cancelled successfully.

        Args:
            bonus_id: Cancelled bonus ID
            cancel_reason: Cancellation reason
            admin_username: Admin who cancelled

        Returns:
            Success message
        """
        safe_admin = escape_markdown(admin_username)

        return (
            f"✅ **Бонус #{bonus_id} успешно отменён!**\n\n"
            f"📝 Причина: {cancel_reason}\n"
            f"👤 Отменил: @{safe_admin}"
        )

    @staticmethod
    def bonus_details(
        bonus: "BonusCredit",
        status_text: str,
        progress: float,
        remaining: Decimal
    ) -> str:
        """
        Detailed bonus information.

        Args:
            bonus: BonusCredit model instance
            status_text: Formatted status text with emoji
            progress: ROI progress percentage
            remaining: Remaining ROI amount

        Returns:
            Bonus details message
        """
        user_name = (
            bonus.user.username
            if bonus.user
            else f"ID:{bonus.user_id}"
        )
        admin_name = (
            bonus.admin.username
            if bonus.admin
            else "система"
        )
        safe_user = escape_markdown(user_name)
        safe_admin = escape_markdown(admin_name)
        safe_reason = escape_markdown(bonus.reason or "не указана")
        date_str = (
            bonus.created_at.strftime("%d.%m.%Y %H:%M")
            if bonus.created_at
            else "н/д"
        )

        return (
            f"🎁 **Бонус #{bonus.id}**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"📊 **Статус:** {status_text}\n\n"
            f"👤 **Получатель:** @{safe_user}\n"
            f"💰 **Сумма:** {format_usdt(bonus.amount)} USDT\n"
            f"🎯 **ROI Cap:** "
            f"{format_usdt(bonus.roi_cap_amount)} USDT\n"
            f"📈 **ROI выплачено:** "
            f"{format_usdt(bonus.roi_paid_amount)} USDT "
            f"({progress:.1f}%)\n"
            f"💵 **Осталось:** {format_usdt(remaining)} USDT\n\n"
            f"📝 **Причина:** _{safe_reason}_\n"
            f"👤 **Начислил:** @{safe_admin}\n"
            f"📅 **Дата:** {date_str}"
        )

    @staticmethod
    def enter_cancel_reason_prompt() -> str:
        """
        Enter cancel reason prompt for answer.

        Returns:
            Prompt text
        """
        return "Введите причину отмены бонуса:"

    @staticmethod
    def enter_cancel_reason_short(bonus_id: int) -> str:
        """
        Short cancel reason prompt for callback.

        Args:
            bonus_id: Bonus ID being cancelled

        Returns:
            Prompt text
        """
        return (
            f"⚠️ **Отмена бонуса #{bonus_id}**\n\n"
            f"Введите причину отмены:"
        )

    @staticmethod
    def cancel_cancelled() -> str:
        """
        Cancel bonus operation cancelled.

        Returns:
            Cancellation message
        """
        return "❌ Отмена бонуса прервана."

    @staticmethod
    def cancel_reason_missing_error() -> str:
        """
        Cancel reason missing in state error.

        Returns:
            Error message
        """
        return "❌ ID бонуса не найден. Попробуйте заново."

    @staticmethod
    def no_active_bonuses_to_cancel() -> str:
        """
        No active bonuses available to cancel.

        Returns:
            Info message
        """
        return (
            "⚠️ **Отмена бонусов**\n\n"
            "Нет активных бонусов для отмены."
        )

    @staticmethod
    def insufficient_permissions_cancel() -> str:
        """
        Insufficient permissions to cancel bonuses.

        Returns:
            Error message
        """
        return (
            "❌ **Недостаточно прав**\n\n"
            "Отмена бонусов доступна только "
            "супер-администратору."
        )

    @staticmethod
    def super_admin_only_cancel() -> str:
        """
        Super admin only can cancel bonuses error.

        Returns:
            Error message
        """
        return "❌ Только супер-админ может отменять бонусы"

    @staticmethod
    def super_admin_only_alert() -> str:
        """
        Alert text for super admin only actions.

        Returns:
            Alert text
        """
        return "❌ Только супер-админ"

    @staticmethod
    def bonus_already_inactive_alert() -> str:
        """
        Bonus already inactive alert.

        Returns:
            Alert text
        """
        return "❌ Бонус уже неактивен"
