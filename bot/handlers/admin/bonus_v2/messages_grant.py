"""
Message templates for Bonus Grant operations.

Contains all messages related to granting bonuses to users.
"""

from decimal import Decimal

from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

# Separator line used throughout messages
SEPARATOR_LINE = "━━━━━━━━━━━━━━━━━━━━━━━━━"


class BonusGrantMessages:
    """Message templates for bonus granting operations."""

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
        safe_username = (
            escape_markdown(user.username)
            if user.username
            else "не указан"
        )

        total_balance = format_usdt(
            user_stats['total_bonus_balance']
        )
        total_roi = format_usdt(
            user_stats['total_bonus_roi_earned']
        )

        return (
            f"✅ **Пользователь найден**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"👤 Username: @{safe_username}\n"
            f"🆔 Telegram ID: `{user.telegram_id}`\n"
            f"📊 Внутренний ID: `{user.id}`\n\n"
            f"💰 **Бонусный баланс:** {total_balance} USDT\n"
            f"📈 **Заработано ROI:** {total_roi} USDT\n"
            f"🟢 **Активных бонусов:** "
            f"{user_stats['active_bonuses_count']}\n\n"
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
        return (
            "📝 **Введите причину вручную:**\n\n"
            "_Минимум 5 символов, максимум 200_"
        )

    @staticmethod
    def grant_step4_confirmation(
        state_data: dict,
        admin,
        amount: Decimal,
        roi_cap: Decimal
    ) -> str:
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
        safe_username = escape_markdown(
            state_data.get("target_username", "")
        )
        safe_reason = escape_markdown(state_data["reason"])
        safe_admin = escape_markdown(
            admin.username or str(admin.telegram_id)
        )

        return (
            f"🎁 **Подтверждение начисления**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"**Шаг 4 из 4:** Проверьте данные\n\n"
            f"👤 **Получатель:** @{safe_username}\n"
            f"🆔 **Telegram ID:** "
            f"`{state_data['target_telegram_id']}`\n\n"
            f"💰 **Сумма бонуса:** {format_usdt(amount)} USDT\n"
            f"🎯 **ROI Cap (500%):** "
            f"{format_usdt(roi_cap)} USDT\n\n"
            f"📝 **Причина:** _{safe_reason}_\n\n"
            f"👤 **Админ:** @{safe_admin}\n\n"
            f"⚠️ **Подтвердите начисление бонуса**"
        )

    @staticmethod
    def grant_success(
        state_data: dict,
        amount: Decimal,
        roi_cap: Decimal,
        bonus_id: int
    ) -> str:
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
        safe_username = escape_markdown(
            state_data.get("target_username", "")
        )
        safe_reason = state_data["reason"]

        return (
            f"✅ **Бонус успешно начислен!**\n"
            f"{SEPARATOR_LINE}\n\n"
            f"👤 Получатель: @{safe_username}\n"
            f"💰 Сумма: **{format_usdt(amount)} USDT**\n"
            f"🎯 ROI Cap: **{format_usdt(roi_cap)} USDT**\n"
            f"📝 Причина: {safe_reason}\n\n"
            f"🆔 ID бонуса: `{bonus_id}`\n\n"
            f"ℹ️ _Бонус начнёт участвовать в начислении ROI "
            f"со следующего расчётного периода._"
        )

    @staticmethod
    def grant_edit_prompt() -> str:
        """
        Prompt for editing grant data.

        Returns:
            Edit prompt message
        """
        return (
            "✏️ **Редактирование**\n\n"
            "Начните заново — введите @username или "
            "Telegram ID пользователя:"
        )

    @staticmethod
    def grant_cancelled() -> str:
        """
        Grant bonus operation cancelled.

        Returns:
            Cancellation message
        """
        return "❌ Начисление бонуса отменено."

    @staticmethod
    def enter_user_data_prompt() -> str:
        """
        Enter user data prompt.

        Returns:
            Prompt text
        """
        return "Введите данные пользователя:"

    @staticmethod
    def insufficient_permissions_grant() -> str:
        """
        Insufficient permissions to grant bonuses.

        Returns:
            Error message
        """
        return (
            "❌ **Недостаточно прав**\n\n"
            "Начисление бонусов доступно только "
            "администраторам."
        )

    @staticmethod
    def bonus_granted_alert() -> str:
        """
        Alert text for bonus granted callback.

        Returns:
            Alert text
        """
        return "✅ Бонус начислен!"
