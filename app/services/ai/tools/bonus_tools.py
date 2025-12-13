"""Bonus management tools."""

from typing import Any


def get_bonus_tools() -> list[dict[str, Any]]:
    """Get bonus management tools."""
    return [
        {
            "name": "grant_bonus",
            "description": (
                "Начислить бонус пользователю. ВАЖНО: только по явной "
                "команде админа!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Сумма бонуса в USDT (1-10000)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина начисления",
                    },
                },
                "required": ["user_identifier", "amount", "reason"],
            },
        },
        {
            "name": "get_user_bonuses",
            "description": "Получить список бонусов пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                    "active_only": {
                        "type": "boolean",
                        "description": "Только активные",
                        "default": False,
                    },
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "cancel_bonus",
            "description": (
                "Отменить активный бонус. ВАЖНО: только по явной "
                "команде админа!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "bonus_id": {
                        "type": "integer",
                        "description": "ID бонуса",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина отмены",
                    },
                },
                "required": ["bonus_id", "reason"],
            },
        },
    ]
