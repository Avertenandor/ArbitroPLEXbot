"""Messaging and broadcast tools."""

from typing import Any

from app.services.ai.prompts import UserRole


def get_messaging_tools(
    role: UserRole = UserRole.SUPER_ADMIN,
) -> list[dict[str, Any]]:
    """Get messaging and broadcast tools based on role."""
    is_commander = role == UserRole.SUPER_ADMIN

    if is_commander:
        broadcast_groups = [
            "active_appeals",
            "active_deposits",
            "active_24h",
            "active_7d",
            "all",
        ]
        default_limit = 100
    else:
        broadcast_groups = [
            "active_appeals",
            "active_deposits",
            "active_24h",
            "active_7d",
        ]
        default_limit = 50

    return [
        {
            "name": "send_message_to_user",
            "description": (
                "Отправить персональное сообщение конкретному "
                "пользователю."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": (
                            "@username, telegram_id или ID:xxx "
                            "пользователя"
                        ),
                    },
                    "message_text": {
                        "type": "string",
                        "description": (
                            "Текст сообщения (поддерживается Markdown)"
                        ),
                    },
                },
                "required": ["user_identifier", "message_text"],
            },
        },
        {
            "name": "broadcast_to_group",
            "description": (
                f"Массовая рассылка сообщения группе пользователей."
                f"{' Лимит: ' + str(default_limit) + ' получателей.' if not is_commander else ''}"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "group": {
                        "type": "string",
                        "enum": broadcast_groups,
                        "description": (
                            "Группа получателей"
                            + (", all (все)" if is_commander else "")
                        ),
                    },
                    "message_text": {
                        "type": "string",
                        "description": "Текст сообщения (Markdown)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            f"Максимум получателей "
                            f"(по умолчанию {default_limit})"
                        ),
                        "default": default_limit,
                    },
                },
                "required": ["group", "message_text"],
            },
        },
        {
            "name": "get_users_list",
            "description": "Получить список пользователей группы.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "group": {
                        "type": "string",
                        "enum": broadcast_groups,
                        "description": "Группа пользователей",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Максимум записей",
                        "default": 20,
                    },
                },
                "required": ["group"],
            },
        },
        {
            "name": "invite_to_dialog",
            "description": (
                "Отправить персональное приглашение к диалогу с Арьей."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                    "custom_message": {
                        "type": "string",
                        "description": "Кастомный текст (опционально)",
                    },
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "mass_invite_to_dialog",
            "description": (
                f"Массовая рассылка приглашений к диалогу."
                f"{' Лимит: ' + str(default_limit) + '.' if not is_commander else ''}"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "group": {
                        "type": "string",
                        "enum": [
                            "active_appeals",
                            "active_deposits",
                            "active_24h",
                            "active_7d",
                        ],
                        "description": "Группа пользователей",
                    },
                    "custom_message": {
                        "type": "string",
                        "description": "Кастомный текст",
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            f"Максимум приглашений "
                            f"(по умолчанию {default_limit})"
                        ),
                        "default": default_limit,
                    },
                },
                "required": ["group"],
            },
        },
        {
            "name": "send_feedback_request",
            "description": (
                "Отправить запрос обратной связи админу. Спросить о "
                "предложениях, проблемах или идеях по улучшению."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id админа",
                    },
                    "topic": {
                        "type": "string",
                        "description": (
                            "Тема опроса (например: 'улучшения бота', "
                            "'проблемы', 'новые функции')"
                        ),
                    },
                    "question": {
                        "type": "string",
                        "description": "Конкретный вопрос для админа",
                    },
                },
                "required": ["admin_identifier", "topic", "question"],
            },
        },
        {
            "name": "broadcast_to_admins",
            "description": (
                "Отправить сообщение всем активным админам. Для "
                "объявлений, опросов или сбора обратной связи."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "message_text": {
                        "type": "string",
                        "description": "Текст сообщения (Markdown)",
                    },
                    "request_feedback": {
                        "type": "boolean",
                        "description": "Добавить кнопку 'Ответить ARIA'",
                        "default": True,
                    },
                },
                "required": ["message_text"],
            },
        },
    ]
