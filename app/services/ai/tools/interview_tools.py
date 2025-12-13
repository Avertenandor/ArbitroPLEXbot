"""Interview tools for conducting interviews with admins."""

from typing import Any


def get_interview_tools() -> list[dict[str, Any]]:
    """Get interview tools for conducting interviews with admins."""
    return [
        {
            "name": "start_interview",
            "description": (
                "Начать интервью с админом. Отправляет вопросы по одному."
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
                        "description": "Тема интервью",
                    },
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Список вопросов (1-10)",
                    },
                },
                "required": ["admin_identifier", "topic", "questions"],
            },
        },
        {
            "name": "get_interview_status",
            "description": "Получить статус активного интервью.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                },
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "cancel_interview",
            "description": "Отменить активное интервью.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                },
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "get_knowledge_by_user",
            "description": (
                "Получить записи базы знаний от конкретного "
                "пользователя/админа. Показывает интервью и записи."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "@username пользователя (без @)",
                    },
                },
                "required": ["username"],
            },
        },
    ]
