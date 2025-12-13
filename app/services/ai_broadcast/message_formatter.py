"""Message formatting utilities for AI Broadcast Service."""


class MessageFormatter:
    """Formats various types of messages for AI Broadcast."""

    @staticmethod
    def format_invitation(
        user_name: str | None = None,
        custom_message: str | None = None,
    ) -> str:
        """
        Format personal invitation message to dialog with ARIA.

        Args:
            user_name: User's username, first name, or None
            custom_message: Optional custom message

        Returns:
            Formatted invitation message
        """
        if custom_message:
            return custom_message

        name = user_name or "друг"
        return (
            f"👋 Привет, {name}!\n\n"
            f"Я **Арья** — AI-помощник ArbitroPLEX.\n\n"
            f"Заметила, что у тебя могут быть вопросы. "
            f"Я здесь, чтобы помочь!\n\n"
            f"Напиши мне прямо сейчас или нажми кнопку "
            f"**💬 Свободный диалог** в меню.\n\n"
            f"С удовольствием отвечу на любые вопросы! 🤗"
        )

    @staticmethod
    def format_mass_invitation(
        user_name: str | None = None,
        custom_message: str | None = None,
    ) -> str:
        """
        Format mass invitation message.

        Args:
            user_name: User's username, first name, or None
            custom_message: Optional custom message template

        Returns:
            Formatted invitation message
        """
        name = user_name or "друг"

        if custom_message:
            return custom_message.replace("{name}", name)

        return (
            f"👋 Привет, {name}!\n\n"
            f"Я **Арья** — AI-помощник ArbitroPLEX.\n\n"
            f"Хочу убедиться, что у тебя всё хорошо и "
            f"ответить на любые вопросы.\n\n"
            f"Напиши мне в **💬 Свободный диалог** — "
            f"я на связи! 🤗"
        )

    @staticmethod
    def format_feedback_request(
        topic: str,
        question: str,
    ) -> str:
        """
        Format feedback request message.

        Args:
            topic: Topic of the feedback request
            question: Specific question to ask

        Returns:
            Formatted feedback request message
        """
        return (
            f"💬 **Запрос обратной связи от ARIA**\n\n"
            f"📋 **Тема:** {topic}\n\n"
            f"❓ **Вопрос:**\n{question}\n\n"
            f"_Пожалуйста, ответьте на это сообщение или "
            f"нажмите '🤖 AI Помощник' чтобы обсудить с ARIA._"
        )

    @staticmethod
    def add_feedback_prompt(message: str) -> str:
        """
        Add feedback prompt to message.

        Args:
            message: Original message text

        Returns:
            Message with feedback prompt appended
        """
        return (
            f"{message}\n\n"
            f"💬 _Есть идеи или предложения? "
            f"Нажмите '🤖 AI Помощник' чтобы обсудить с ARIA._"
        )

    @staticmethod
    def format_broadcast_result(
        group: str,
        total: int,
        sent: int,
        failed: int,
    ) -> str:
        """
        Format broadcast result message.

        Args:
            group: Target group name
            total: Total number of users
            sent: Number of successfully sent messages
            failed: Number of failed messages

        Returns:
            Formatted result message
        """
        return f"Отправлено {sent} из {total} сообщений"

    @staticmethod
    def format_mass_invite_result(
        group: str,
        total: int,
        sent: int,
        failed: int,
    ) -> str:
        """
        Format mass invite result message.

        Args:
            group: Target group name
            total: Total number of users
            sent: Number of successfully sent invitations
            failed: Number of failed invitations

        Returns:
            Formatted result message
        """
        return f"Приглашения отправлены: {sent} из {total}"

    @staticmethod
    def format_admin_broadcast_result(
        sent: int,
    ) -> str:
        """
        Format admin broadcast result message.

        Args:
            sent: Number of successfully sent messages

        Returns:
            Formatted result message
        """
        return f"Отправлено {sent} админам"
