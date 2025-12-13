"""User inquiries management tools."""

from typing import Any


def get_inquiries_tools() -> list[dict[str, Any]]:
    """Get user inquiries management tools."""
    return [
        {
            "name": "get_inquiries_list",
            "description": "Получить список обращений пользователей.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["new", "in_progress", "closed"],
                        "description": "Фильтр по статусу",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Максимум записей",
                        "default": 20,
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_inquiry_details",
            "description": "Получить детали обращения с перепиской.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "inquiry_id": {
                        "type": "integer",
                        "description": "ID обращения",
                    },
                },
                "required": ["inquiry_id"],
            },
        },
        {
            "name": "take_inquiry",
            "description": "Взять обращение в работу.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "inquiry_id": {
                        "type": "integer",
                        "description": "ID обращения",
                    },
                },
                "required": ["inquiry_id"],
            },
        },
        {
            "name": "reply_to_inquiry",
            "description": "Ответить на обращение пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "inquiry_id": {
                        "type": "integer",
                        "description": "ID обращения",
                    },
                    "message": {
                        "type": "string",
                        "description": "Текст ответа",
                    },
                },
                "required": ["inquiry_id", "message"],
            },
        },
        {
            "name": "close_inquiry",
            "description": "Закрыть обращение.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "inquiry_id": {
                        "type": "integer",
                        "description": "ID обращения",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина закрытия",
                    },
                },
                "required": ["inquiry_id"],
            },
        },
    ]
