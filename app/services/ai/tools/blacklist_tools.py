"""Blacklist management tools."""

from typing import Any


def get_blacklist_tools() -> list[dict[str, Any]]:
    """Get blacklist management tools."""
    return [
        {
            "name": "get_blacklist",
            "description": "Получить чёрный список.",
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
            "name": "check_blacklist",
            "description": "Проверить наличие в чёрном списке.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": (
                            "@username, telegram_id или wallet"
                        ),
                    },
                },
                "required": ["identifier"],
            },
        },
        {
            "name": "add_to_blacklist",
            "description": (
                "Добавить в чёрный список. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": (
                            "@username, telegram_id или wallet"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина",
                    },
                    "action_type": {
                        "type": "string",
                        "enum": ["pre_block", "post_block", "termination"],
                        "description": "Тип блокировки",
                    },
                },
                "required": ["identifier", "reason"],
            },
        },
        {
            "name": "remove_from_blacklist",
            "description": (
                "Удалить из чёрного списка. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": (
                            "@username, telegram_id или wallet"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина удаления",
                    },
                },
                "required": ["identifier", "reason"],
            },
        },
    ]
