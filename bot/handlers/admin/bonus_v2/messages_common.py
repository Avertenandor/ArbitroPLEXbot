"""
Common message templates for Bonus Management.

Contains common error messages and utility messages used across
different bonus operations.
"""


class BonusCommonMessages:
    """Common message templates for bonus management."""

    @staticmethod
    def invalid_amount() -> str:
        """
        Invalid amount error.

        Returns:
            Error message
        """
        return (
            "❌ **Неверная сумма**\n\n"
            "Введите число от 1 до 100,000\n"
            "_Например: `100` или `50.5`_"
        )

    @staticmethod
    def reason_too_short() -> str:
        """
        Reason too short error.

        Returns:
            Error message
        """
        return (
            "❌ Причина слишком короткая. "
            "Минимум 5 символов."
        )

    @staticmethod
    def reason_too_long() -> str:
        """
        Reason too long error.

        Returns:
            Error message
        """
        return (
            "❌ Причина слишком длинная. "
            "Максимум 200 символов."
        )

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
    def operation_cancelled() -> str:
        """
        Generic operation cancelled message.

        Returns:
            Cancellation message
        """
        return "❌ Операция отменена."

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
