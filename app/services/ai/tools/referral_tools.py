"""Referral statistics tools."""

from typing import Any


def get_referral_tools() -> list[dict[str, Any]]:
    """Get referral statistics tools."""
    return [
        {
            "name": "get_platform_referral_stats",
            "description": "Получить реферальную статистику платформы.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_user_referrals",
            "description": "Получить рефералов пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Макс. кол-во",
                    },
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "get_top_referrers",
            "description": (
                "Получить топ рефереров по кол-ву приглашённых."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Кол-во в топе",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_top_earners",
            "description": "Получить топ рефереров по заработку.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Кол-во в топе",
                    },
                },
                "required": [],
            },
        },
    ]
