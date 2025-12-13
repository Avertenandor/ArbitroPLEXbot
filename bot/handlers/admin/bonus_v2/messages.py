"""
Message templates for Bonus Management V2.

All message strings centralized for easy maintenance and localization.
This module now serves as the main entry point and delegates to
specialized message modules.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from bot.handlers.admin.bonus_v2.messages_common import (
    BonusCommonMessages,
)
from bot.handlers.admin.bonus_v2.messages_grant import (
    BonusGrantMessages,
)
from bot.handlers.admin.bonus_v2.messages_history import (
    BonusHistoryMessages,
)
from bot.handlers.admin.bonus_v2.messages_search import (
    BonusSearchMessages,
)
from bot.handlers.admin.bonus_v2.messages_view import (
    BonusViewMessages,
)
from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

if TYPE_CHECKING:
    from app.models.bonus_credit import BonusCredit

# Separator line used throughout messages
SEPARATOR_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"


class BonusMessages:
    """
    Static message templates for bonus management.

    This class serves as the main interface and delegates calls to
    specialized message classes for different operations:
    - BonusGrantMessages: Grant/create bonus operations
    - BonusViewMessages: View and cancel bonus operations
    - BonusSearchMessages: Search user bonuses
    """

    # ============ MAIN MENU AND STATS ============

    @staticmethod
    def main_menu(
        stats: dict,
        role_display: str,
        permissions: dict
    ) -> str:
        """
        Main bonus menu message.

        Args:
            stats: Global bonus statistics dict
            role_display: Display name for admin role
            permissions: Permissions dict for the role

        Returns:
            Formatted main menu message
        """
        # Build permissions text
        perm_text = []
        if permissions["can_grant"]:
            perm_text.append("✅ начисление")
        if permissions["can_cancel_any"]:
            perm_text.append("✅ отмена любых")
        elif permissions["can_cancel_own"]:
            perm_text.append("✅ отмена своих")
        if permissions["can_view"]:
            perm_text.append("✅ просмотр")

        total_granted = format_usdt(stats.get('total_granted', 0))
        last_24h = format_usdt(stats.get('last_24h', 0))

        return (
            f"🎁 **Управление бонусами**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"👤 Вы: {role_display}\n"
            f"🔐 Права: {', '.join(perm_text)}\n\n"
            f"📊 **Общая статистика:**\n"
            f"├ 💰 Всего начислено: **{total_granted}** USDT\n"
            f"├ 🟢 Активных: **{stats.get('active_count', 0)}** "
            f"бонусов\n"
            f"├ 📅 За 24 часа: **{last_24h}** USDT\n"
            f"└ 📋 Всего записей: **{stats.get('total_count', 0)}**\n\n"
            f"_Выберите действие:_"
        )

    @staticmethod
    def detailed_stats(
        stats: dict,
        active_sum: Decimal,
        completed_sum: Decimal,
        cancelled_sum: Decimal
    ) -> str:
        """
        Detailed statistics message.

        Args:
            stats: Global bonus statistics dict
            active_sum: Sum of active bonuses
            completed_sum: Sum of completed bonuses
            cancelled_sum: Sum of cancelled bonuses

        Returns:
            Formatted detailed statistics message
        """
        total_granted = format_usdt(stats.get('total_granted', 0))
        last_24h = format_usdt(stats.get('last_24h', 0))

        return (
            f"📊 **Детальная статистика бонусов**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"💰 **Общие суммы:**\n"
            f"├ Всего начислено: **{total_granted}** USDT\n"
            f"├ За последние 24ч: **{last_24h}** USDT\n"
            f"└ Всего записей: **{stats.get('total_count', 0)}**\n\n"
            f"📈 **По статусам (последние 50):**\n"
            f"├ 🟢 Активные: **{format_usdt(active_sum)}** USDT\n"
            f"├ ✅ Завершённые: "
            f"**{format_usdt(completed_sum)}** USDT\n"
            f"└ ❌ Отменённые: "
            f"**{format_usdt(cancelled_sum)}** USDT\n\n"
            f"ℹ️ _Бонус считается завершённым когда "
            f"выплачен весь ROI Cap (500%)_"
        )

    # ============ BONUS HISTORY (DELEGATED) ============

    @staticmethod
    def bonus_history_header() -> str:
        """Delegate to BonusHistoryMessages."""
        return BonusHistoryMessages.bonus_history_header()

    @staticmethod
    def bonus_history_item(
        bonus: "BonusCredit",
        status_emoji: str,
        progress: str = "",
    ) -> str:
        """Delegate to BonusHistoryMessages."""
        return BonusHistoryMessages.bonus_history_item(
            bonus, status_emoji, progress
        )

    @staticmethod
    def bonus_history_footer() -> str:
        """Delegate to BonusHistoryMessages."""
        return BonusHistoryMessages.bonus_history_footer()

    @staticmethod
    def bonus_history_empty() -> str:
        """Delegate to BonusHistoryMessages."""
        return BonusHistoryMessages.bonus_history_empty()

    # ============ MY BONUSES (DELEGATED) ============

    @staticmethod
    def my_bonuses(
        my_bonuses: list,
        total: Decimal,
        active_count: int
    ) -> str:
        """Delegate to BonusHistoryMessages."""
        return BonusHistoryMessages.my_bonuses(
            my_bonuses, total, active_count
        )

    @staticmethod
    def my_bonuses_empty() -> str:
        """Delegate to BonusHistoryMessages."""
        return BonusHistoryMessages.my_bonuses_empty()

    # ============ GRANT OPERATIONS (DELEGATED) ============

    @staticmethod
    def grant_step1() -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.grant_step1()

    @staticmethod
    def grant_step2_user_found(user, user_stats: dict) -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.grant_step2_user_found(
            user, user_stats
        )

    @staticmethod
    def grant_step2_manual_amount() -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.grant_step2_manual_amount()

    @staticmethod
    def grant_step3_amount(
        amount: Decimal,
        roi_cap: Decimal
    ) -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.grant_step3_amount(amount, roi_cap)

    @staticmethod
    def grant_step3_custom_reason() -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.grant_step3_custom_reason()

    @staticmethod
    def grant_step4_confirmation(
        state_data: dict,
        admin,
        amount: Decimal,
        roi_cap: Decimal
    ) -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.grant_step4_confirmation(
            state_data, admin, amount, roi_cap
        )

    @staticmethod
    def grant_success(
        state_data: dict,
        amount: Decimal,
        roi_cap: Decimal,
        bonus_id: int
    ) -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.grant_success(
            state_data, amount, roi_cap, bonus_id
        )

    @staticmethod
    def grant_edit_prompt() -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.grant_edit_prompt()

    @staticmethod
    def grant_cancelled() -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.grant_cancelled()

    @staticmethod
    def enter_user_data_prompt() -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.enter_user_data_prompt()

    @staticmethod
    def insufficient_permissions_grant() -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.insufficient_permissions_grant()

    @staticmethod
    def bonus_granted_alert() -> str:
        """Delegate to BonusGrantMessages."""
        return BonusGrantMessages.bonus_granted_alert()

    # ============ SEARCH OPERATIONS (DELEGATED) ============

    @staticmethod
    def search_user_prompt() -> str:
        """Delegate to BonusSearchMessages."""
        return BonusSearchMessages.search_user_prompt()

    @staticmethod
    def search_user_result(
        user,
        user_stats: dict,
        active_bonuses: list
    ) -> str:
        """Delegate to BonusSearchMessages."""
        return BonusSearchMessages.search_user_result(
            user, user_stats, active_bonuses
        )

    @staticmethod
    def user_not_found(user_input: str) -> str:
        """Delegate to BonusSearchMessages."""
        return BonusSearchMessages.user_not_found(user_input)

    # ============ VIEW/CANCEL OPERATIONS (DELEGATED) ============

    @staticmethod
    def cancel_bonus_list_header() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.cancel_bonus_list_header()

    @staticmethod
    def cancel_bonus_item(
        bonus: "BonusCredit",
        progress: float
    ) -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.cancel_bonus_item(bonus, progress)

    @staticmethod
    def cancel_bonus_list_footer() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.cancel_bonus_list_footer()

    @staticmethod
    def cancel_confirm(
        bonus_id: int,
        user_name: str,
        amount: Decimal,
        reason: str
    ) -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.cancel_confirm(
            bonus_id, user_name, amount, reason
        )

    @staticmethod
    def cancel_success(
        bonus_id: int,
        cancel_reason: str,
        admin_username: str
    ) -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.cancel_success(
            bonus_id, cancel_reason, admin_username
        )

    @staticmethod
    def bonus_details(
        bonus: "BonusCredit",
        status_text: str,
        progress: float,
        remaining: Decimal
    ) -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.bonus_details(
            bonus, status_text, progress, remaining
        )

    @staticmethod
    def enter_cancel_reason_prompt() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.enter_cancel_reason_prompt()

    @staticmethod
    def enter_cancel_reason_short(bonus_id: int) -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.enter_cancel_reason_short(bonus_id)

    @staticmethod
    def cancel_cancelled() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.cancel_cancelled()

    @staticmethod
    def cancel_reason_missing_error() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.cancel_reason_missing_error()

    @staticmethod
    def no_active_bonuses_to_cancel() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.no_active_bonuses_to_cancel()

    @staticmethod
    def insufficient_permissions_cancel() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.insufficient_permissions_cancel()

    @staticmethod
    def super_admin_only_cancel() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.super_admin_only_cancel()

    @staticmethod
    def super_admin_only_alert() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.super_admin_only_alert()

    @staticmethod
    def bonus_already_inactive_alert() -> str:
        """Delegate to BonusViewMessages."""
        return BonusViewMessages.bonus_already_inactive_alert()

    # ============ COMMON ERROR MESSAGES (DELEGATED) ============

    @staticmethod
    def invalid_amount() -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.invalid_amount()

    @staticmethod
    def reason_too_short() -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.reason_too_short()

    @staticmethod
    def reason_too_long() -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.reason_too_long()

    @staticmethod
    def bonus_not_found(bonus_id: int) -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.bonus_not_found(bonus_id)

    @staticmethod
    def operation_cancelled() -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.operation_cancelled()

    @staticmethod
    def back_to_admin_panel() -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.back_to_admin_panel()

    @staticmethod
    def back_to_bonus_menu() -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.back_to_bonus_menu()

    @staticmethod
    def select_next_action() -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.select_next_action()

    @staticmethod
    def select_action() -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.select_action()

    @staticmethod
    def error_with_message(error_msg: str) -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.error_with_message(error_msg)

    @staticmethod
    def error_alert() -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.error_alert()

    @staticmethod
    def bonus_not_found_alert(bonus_id: int) -> str:
        """Delegate to BonusCommonMessages."""
        return BonusCommonMessages.bonus_not_found_alert(bonus_id)
