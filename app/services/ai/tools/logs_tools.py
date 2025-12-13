"""Admin logs tools."""

from typing import Any


def get_logs_tools() -> list[dict[str, Any]]:
    """Get admin logs tools."""
    return [
        {
            "name": "get_recent_logs",
            "description": "Получить последние действия админов.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Кол-во записей",
                    },
                    "action_type": {
                        "type": "string",
                        "description": "Фильтр по типу",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_admin_activity",
            "description": "Получить активность конкретного админа.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Кол-во записей",
                    },
                },
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "search_logs",
            "description": "Поиск в логах действий.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "ID целевого пользователя",
                    },
                    "action_type": {
                        "type": "string",
                        "description": "Тип действия",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Кол-во записей",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_action_types_stats",
            "description": "Получить статистику типов действий.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]
