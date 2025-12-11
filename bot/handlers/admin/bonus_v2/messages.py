"""
Message templates for Bonus Management V2.

All message strings centralized in one place for easy maintenance and localization.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

if TYPE_CHECKING:
    from app.models.bonus_credit import BonusCredit

# Separator line used throughout messages
SEPARATOR_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"


class BonusMessages:
    """Static message templates for bonus management."""

    @staticmethod
    def main_menu(stats: dict, role_display: str, permissions: dict) -> str:
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

        return (
            f"🎁 **Управление бонусами**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"👤 Вы: {role_display}\n"
            f"🔐 Права: {', '.join(perm_text)}\n\n"
            f"📊 **Общая статистика:**\n"
            f"├ 💰 Всего начислено: **{format_usdt(stats.get('total_granted', 0))}** USDT\n"
            f"├ 🟢 Активных: **{stats.get('active_count', 0)}** бонусов\n"
            f"├ 📅 За 24 часа: **{format_usdt(stats.get('last_24h', 0))}** USDT\n"
            f"└ 📋 Всего записей: **{stats.get('total_count', 0)}**\n\n"
            f"_Выберите действие:_"
        )

    @staticmethod
    def detailed_stats(stats: dict, active_sum: Decimal, completed_sum: Decimal, cancelled_sum: Decimal) -> str:
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
        return (
            f"📊 **Детальная статистика бонусов**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"💰 **Общие суммы:**\n"
            f"├ Всего начислено: **{format_usdt(stats.get('total_granted', 0))}** USDT\n"
            f"├ За последние 24ч: **{format_usdt(stats.get('last_24h', 0))}** USDT\n"
            f"└ Всего записей: **{stats.get('total_count', 0)}**\n\n"
            f"📈 **По статусам (последние 50):**\n"
            f"├ 🟢 Активные: **{format_usdt(active_sum)}** USDT\n"
            f"├ ✅ Завершённые: **{format_usdt(completed_sum)}** USDT\n"
            f"└ ❌ Отменённые: **{format_usdt(cancelled_sum)}** USDT\n\n"
            f"ℹ️ _Бонус считается завершённым когда выплачен весь ROI Cap (500%)_"
        )

    @staticmethod
    def bonus_history_header() -> str:
        """
        Bonus history header.

        Returns:
            Formatted history header
        """
        return f"📋 **Последние 15 бонусов:**\n{SEPARATOR_LINE}\n\n"

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
        admin_name = bonus.admin.username if bonus.admin else "система"
        user_name = bonus.user.username if bonus.user else f"ID:{bonus.user_id}"
        safe_user = escape_markdown(user_name) if user_name else str(bonus.user_id)
        safe_admin = escape_markdown(admin_name) if admin_name else "система"

        reason_short = (bonus.reason or "")[:25]
        if len(bonus.reason or "") > 25:
            reason_short += "..."

        return (
            f"{status_emoji} **{format_usdt(bonus.amount)}** → @{safe_user}{progress}\n"
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
        return "📋 **История бонусов пуста**\n\nЕщё не было начислено ни одного бонуса."

    @staticmethod
    def my_bonuses(my_bonuses: list, total: Decimal, active_count: int) -> str:
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
            f"📊 Всего: **{len(my_bonuses)}** бонусов на **{format_usdt(total)}** USDT\n"
            f"🟢 Активных: **{active_count}**\n\n"
        )

        for b in my_bonuses[:10]:
            from bot.handlers.admin.bonus_management_v2 import get_bonus_status_emoji

            status = get_bonus_status_emoji(b)
            user_name = b.user.username if b.user else f"ID:{b.user_id}"
            safe_user = escape_markdown(user_name)

            text += f"{status} **{format_usdt(b.amount)}** → @{safe_user}\n"

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
        return "📑 **Ваши начисления**\n\nВы ещё не начислили ни одного бонуса."

    @staticmethod
    def grant_step1() -> str:
        """
        Step 1: Enter user to grant bonus.

        Returns:
            Grant step 1 message
        """
        return (
            "➕ **Начисление бонуса**\n"
            f"{SEPARATOR_LINE}\n\n"
            "**Шаг 1 из 4:** Укажите получателя\n\n"
            "Введите данные пользователя:\n"
            "• `@username` — по юзернейму\n"
            "• `123456789` — по Telegram ID\n"
            "• `ID:42` — по внутреннему ID\n\n"
            "_Или нажмите «Отмена» для возврата_"
        )

    @staticmethod
    def grant_step2_user_found(user, user_stats: dict) -> str:
        """
        Step 2: User found, enter amount.

        Args:
            user: User model instance
            user_stats: User bonus statistics dict

        Returns:
            Grant step 2 message
        """
        safe_username = escape_markdown(user.username) if user.username else "не указан"

        return (
            f"✅ **Пользователь найден**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"👤 Username: @{safe_username}\n"
            f"🆔 Telegram ID: `{user.telegram_id}`\n"
            f"📊 Внутренний ID: `{user.id}`\n\n"
            f"💰 **Бонусный баланс:** {format_usdt(user_stats['total_bonus_balance'])} USDT\n"
            f"📈 **Заработано ROI:** {format_usdt(user_stats['total_bonus_roi_earned'])} USDT\n"
            f"🟢 **Активных бонусов:** {user_stats['active_bonuses_count']}\n\n"
            f"{SEPARATOR_LINE}\n"
            f"**Шаг 2 из 4:** Выберите сумму бонуса"
        )

    @staticmethod
    def grant_step2_manual_amount() -> str:
        """
        Manual amount entry prompt.

        Returns:
            Manual amount entry message
        """
        return (
            "💵 **Ввод суммы вручную**\n\n"
            "Введите сумму бонуса в USDT:\n"
            "• Минимум: 1 USDT\n"
            "• Максимум: 100,000 USDT\n\n"
            "_Например: `150` или `75.50`_"
        )

    @staticmethod
    def grant_step3_amount(amount: Decimal, roi_cap: Decimal) -> str:
        """
        Step 3: Amount confirmed, select reason.

        Args:
            amount: Bonus amount
            roi_cap: ROI cap (500% of amount)

        Returns:
            Grant step 3 message
        """
        return (
            f"💰 **Сумма:** {format_usdt(amount)} USDT\n"
            f"🎯 **ROI Cap (500%):** {format_usdt(roi_cap)} USDT\n\n"
            f"{SEPARATOR_LINE}\n"
            f"**Шаг 3 из 4:** Выберите причину начисления\n\n"
            f"_Нажмите на шаблон или введите свою причину:_"
        )

    @staticmethod
    def grant_step3_custom_reason() -> str:
        """
        Custom reason entry prompt.

        Returns:
            Custom reason entry message
        """
        return "📝 **Введите причину вручную:**\n\n_Минимум 5 символов, максимум 200_"

    @staticmethod
    def grant_step4_confirmation(state_data: dict, admin, amount: Decimal, roi_cap: Decimal) -> str:
        """
        Step 4: Final confirmation.

        Args:
            state_data: FSM state data with grant details
            admin: Admin model instance
            amount: Bonus amount
            roi_cap: ROI cap amount

        Returns:
            Grant confirmation message
        """
        safe_username = escape_markdown(state_data.get("target_username", ""))
        safe_reason = escape_markdown(state_data["reason"])
        safe_admin = escape_markdown(admin.username or str(admin.telegram_id))

        return (
            f"🎁 **Подтверждение начисления**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"**Шаг 4 из 4:** Проверьте данные\n\n"
            f"👤 **Получатель:** @{safe_username}\n"
            f"🆔 **Telegram ID:** `{state_data['target_telegram_id']}`\n\n"
            f"💰 **Сумма бонуса:** {format_usdt(amount)} USDT\n"
            f"🎯 **ROI Cap (500%):** {format_usdt(roi_cap)} USDT\n\n"
            f"📝 **Причина:** _{safe_reason}_\n\n"
            f"👤 **Админ:** @{safe_admin}\n\n"
            f"⚠️ **Подтвердите начисление бонуса**"
        )

    @staticmethod
    def grant_success(state_data: dict, amount: Decimal, roi_cap: Decimal, bonus_id: int) -> str:
        """
        Bonus granted successfully.

        Args:
            state_data: FSM state data with grant details
            amount: Bonus amount
            roi_cap: ROI cap amount
            bonus_id: Created bonus ID

        Returns:
            Success message
        """
        safe_username = escape_markdown(state_data.get("target_username", ""))
        safe_reason = state_data["reason"]

        return (
            f"✅ **Бонус успешно начислен!**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"👤 Получатель: @{safe_username}\n"
            f"💰 Сумма: **{format_usdt(amount)} USDT**\n"
            f"🎯 ROI Cap: **{format_usdt(roi_cap)} USDT**\n"
            f"📝 Причина: {safe_reason}\n\n"
            f"🆔 ID бонуса: `{bonus_id}`\n\n"
            f"ℹ️ _Бонус начнёт участвовать в начислении ROI со следующего расчётного периода._"
        )

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
    def search_user_result(user, user_stats: dict, active_bonuses: list) -> str:
        """
        Search user result.

        Args:
            user: User model instance
            user_stats: User bonus statistics dict
            active_bonuses: List of active bonuses (up to 5 shown)

        Returns:
            Search result message
        """
        safe_username = escape_markdown(user.username) if user.username else str(user.telegram_id)

        text = (
            f"👤 **Бонусы пользователя @{safe_username}**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"💰 Бонусный баланс: **{format_usdt(user_stats['total_bonus_balance'])} USDT**\n"
            f"📈 Заработано ROI: **{format_usdt(user_stats['total_bonus_roi_earned'])} USDT**\n"
            f"🟢 Активных: **{user_stats['active_bonuses_count']}**\n"
            f"📋 Всего: **{user_stats['total_bonuses_count']}**\n\n"
        )

        if active_bonuses:
            text += "**Активные бонусы:**\n"
            for bonus in active_bonuses[:5]:
                progress = bonus.roi_progress_percent if hasattr(bonus, "roi_progress_percent") else 0
                text += f"• ID `{bonus.id}`: {format_usdt(bonus.amount)} USDT (ROI: {progress:.0f}%)\n"

        return text

    @staticmethod
    def cancel_bonus_list_header() -> str:
        """
        Cancel bonus list header.

        Returns:
            Cancel list header
        """
        return f"⚠️ **Отмена бонусов**\n{SEPARATOR_LINE}\n\n**Активные бонусы:**\n\n"

    @staticmethod
    def cancel_bonus_item(bonus: "BonusCredit", progress: float) -> str:
        """
        Cancel bonus list item.

        Args:
            bonus: BonusCredit model instance
            progress: ROI progress percentage

        Returns:
            Cancel list item
        """
        user_name = bonus.user.username if bonus.user else f"ID:{bonus.user_id}"
        safe_user = escape_markdown(user_name)

        reason_short = (bonus.reason or "")[:20]
        if len(bonus.reason or "") > 20:
            reason_short += "..."

        return (
            f"🟢 **ID {bonus.id}:** {format_usdt(bonus.amount)} USDT → @{safe_user}\n"
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
    def cancel_confirm(bonus_id: int, user_name: str, amount: Decimal, reason: str) -> str:
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
    def cancel_success(bonus_id: int, cancel_reason: str, admin_username: str) -> str:
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
    def bonus_details(bonus: "BonusCredit", status_text: str, progress: float, remaining: Decimal) -> str:
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
        user_name = bonus.user.username if bonus.user else f"ID:{bonus.user_id}"
        admin_name = bonus.admin.username if bonus.admin else "система"
        safe_user = escape_markdown(user_name)
        safe_admin = escape_markdown(admin_name)
        safe_reason = escape_markdown(bonus.reason or "не указана")
        date_str = bonus.created_at.strftime("%d.%m.%Y %H:%M") if bonus.created_at else "н/д"

        return (
            f"🎁 **Бонус #{bonus.id}**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"📊 **Статус:** {status_text}\n\n"
            f"👤 **Получатель:** @{safe_user}\n"
            f"💰 **Сумма:** {format_usdt(bonus.amount)} USDT\n"
            f"🎯 **ROI Cap:** {format_usdt(bonus.roi_cap_amount)} USDT\n"
            f"📈 **ROI выплачено:** {format_usdt(bonus.roi_paid_amount)} USDT ({progress:.1f}%)\n"
            f"💵 **Осталось:** {format_usdt(remaining)} USDT\n\n"
            f"📝 **Причина:** _{safe_reason}_\n"
            f"👤 **Начислил:** @{safe_admin}\n"
            f"📅 **Дата:** {date_str}"
        )

    # ============ ERROR MESSAGES ============

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

    @staticmethod
    def invalid_amount() -> str:
        """
        Invalid amount error.

        Returns:
            Error message
        """
        return "❌ **Неверная сумма**\n\nВведите число от 1 до 100,000\n_Например: `100` или `50.5`_"

    @staticmethod
    def reason_too_short() -> str:
        """
        Reason too short error.

        Returns:
            Error message
        """
        return "❌ Причина слишком короткая. Минимум 5 символов."

    @staticmethod
    def reason_too_long() -> str:
        """
        Reason too long error.

        Returns:
            Error message
        """
        return "❌ Причина слишком длинная. Максимум 200 символов."

    @staticmethod
    def bonus_not_found(bonus_id: int) -> str:
        """
        Bonus not found error.

        Args:
            bonus_id: Bonus ID that was not found

        Returns:
            Error message
        """
        return f"❌ Бонус #{bonus_id} не найден."

    @staticmethod
    def insufficient_permissions_grant() -> str:
        """
        Insufficient permissions to grant bonuses.

        Returns:
            Error message
        """
        return "❌ **Недостаточно прав**\n\nНачисление бонусов доступно только администраторам."

    @staticmethod
    def insufficient_permissions_cancel() -> str:
        """
        Insufficient permissions to cancel bonuses.

        Returns:
            Error message
        """
        return "❌ **Недостаточно прав**\n\nОтмена бонусов доступна только супер-администратору."

    @staticmethod
    def no_active_bonuses_to_cancel() -> str:
        """
        No active bonuses available to cancel.

        Returns:
            Info message
        """
        return "⚠️ **Отмена бонусов**\n\nНет активных бонусов для отмены."

    @staticmethod
    def operation_cancelled() -> str:
        """
        Generic operation cancelled message.

        Returns:
            Cancellation message
        """
        return "❌ Операция отменена."

    @staticmethod
    def grant_cancelled() -> str:
        """
        Grant bonus operation cancelled.

        Returns:
            Cancellation message
        """
        return "❌ Начисление бонуса отменено."

    @staticmethod
    def cancel_cancelled() -> str:
        """
        Cancel bonus operation cancelled.

        Returns:
            Cancellation message
        """
        return "❌ Отмена бонуса прервана."

    @staticmethod
    def grant_edit_prompt() -> str:
        """
        Prompt for editing grant data.

        Returns:
            Edit prompt message
        """
        return "✏️ **Редактирование**\n\nНачните заново — введите @username или Telegram ID пользователя:"

    @staticmethod
    def back_to_admin_panel() -> str:
        """
        Returning to admin panel message.

        Returns:
            Back message
        """
        return "👑 Возвращаюсь в админ-панель..."

    @staticmethod
    def back_to_bonus_menu() -> str:
        """
        Returning to bonus menu message.

        Returns:
            Back message
        """
        return "◀️ Возврат в меню бонусов..."

    @staticmethod
    def select_next_action() -> str:
        """
        Generic select next action prompt.

        Returns:
            Action prompt
        """
        return "Выберите следующее действие:"

    @staticmethod
    def select_action() -> str:
        """
        Generic select action prompt.

        Returns:
            Action prompt
        """
        return "Выберите действие:"

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
        return f"⚠️ **Отмена бонуса #{bonus_id}**\n\nВведите причину отмены:"

    @staticmethod
    def enter_user_data_prompt() -> str:
        """
        Enter user data prompt.

        Returns:
            Prompt text
        """
        return "Введите данные пользователя:"

    @staticmethod
    def error_with_message(error_msg: str) -> str:
        """
        Generic error message wrapper.

        Args:
            error_msg: The error message to display

        Returns:
            Formatted error message
        """
        return f"❌ **Ошибка:** {error_msg}"

    @staticmethod
    def bonus_granted_alert() -> str:
        """
        Alert text for bonus granted callback.

        Returns:
            Alert text
        """
        return "✅ Бонус начислен!"

    @staticmethod
    def super_admin_only_alert() -> str:
        """
        Alert text for super admin only actions.

        Returns:
            Alert text
        """
        return "❌ Только супер-админ"

    @staticmethod
    def error_alert() -> str:
        """
        Generic error alert.

        Returns:
            Alert text
        """
        return "Ошибка!"

    @staticmethod
    def bonus_not_found_alert(bonus_id: int) -> str:
        """
        Bonus not found alert.

        Args:
            bonus_id: Bonus ID that was not found

        Returns:
            Alert text
        """
        return "❌ Бонус не найден"

    @staticmethod
    def bonus_already_inactive_alert() -> str:
        """
        Bonus already inactive alert.

        Returns:
            Alert text
        """
        return "❌ Бонус уже неактивен"

    @staticmethod
    def cancel_reason_missing_error() -> str:
        """
        Cancel reason missing in state error.

        Returns:
            Error message
        """
        return "❌ ID бонуса не найден. Попробуйте заново."

    @staticmethod
    def super_admin_only_cancel() -> str:
        """
        Super admin only can cancel bonuses error.

        Returns:
            Error message
        """
        return "❌ Только супер-админ может отменять бонусы"
