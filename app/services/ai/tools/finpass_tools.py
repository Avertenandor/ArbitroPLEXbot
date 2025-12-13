"""Financial password recovery tools."""

from typing import Any


def get_finpass_tools() -> list[dict[str, Any]]:
    """Get financial password recovery tools."""
    return [
        {
            "name": "get_finpass_requests",
            "description": (
                "Получить заявки на восстановление финпароля."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Макс. кол-во",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_finpass_request_details",
            "description": "Получить детали заявки на восстановление.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "integer",
                        "description": "ID заявки",
                    },
                },
                "required": ["request_id"],
            },
        },
        {
            "name": "approve_finpass_request",
            "description": (
                "Одобрить заявку. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "integer",
                        "description": "ID заявки",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Заметки",
                    },
                },
                "required": ["request_id"],
            },
        },
        {
            "name": "reject_finpass_request",
            "description": (
                "Отклонить заявку. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "integer",
                        "description": "ID заявки",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина отклонения",
                    },
                },
                "required": ["request_id", "reason"],
            },
        },
        {
            "name": "get_finpass_stats",
            "description": "Получить статистику заявок.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]
