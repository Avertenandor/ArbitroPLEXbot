"""Appeals management tools."""

from typing import Any


def get_appeals_tools() -> list[dict[str, Any]]:
    """Get appeals management tools."""
    return [
        {
            "name": "get_appeals_list",
            "description": "Получить список обращений пользователей.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "under_review",
                            "approved",
                            "rejected",
                        ],
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
            "name": "get_appeal_details",
            "description": "Получить детали обращения по ID.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "appeal_id": {
                        "type": "integer",
                        "description": "ID обращения",
                    },
                },
                "required": ["appeal_id"],
            },
        },
        {
            "name": "take_appeal",
            "description": (
                "Взять обращение на рассмотрение. ТОЛЬКО по команде "
                "админа!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "appeal_id": {
                        "type": "integer",
                        "description": "ID обращения",
                    },
                },
                "required": ["appeal_id"],
            },
        },
        {
            "name": "resolve_appeal",
            "description": (
                "Закрыть обращение с решением. ТОЛЬКО по команде админа!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "appeal_id": {
                        "type": "integer",
                        "description": "ID обращения",
                    },
                    "decision": {
                        "type": "string",
                        "enum": ["approve", "reject"],
                        "description": "Решение",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Комментарий",
                    },
                },
                "required": ["appeal_id", "decision"],
            },
        },
        {
            "name": "reply_to_appeal",
            "description": "Отправить ответ пользователю по обращению.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "appeal_id": {
                        "type": "integer",
                        "description": "ID обращения",
                    },
                    "message": {
                        "type": "string",
                        "description": "Текст ответа",
                    },
                },
                "required": ["appeal_id", "message"],
            },
        },
    ]
