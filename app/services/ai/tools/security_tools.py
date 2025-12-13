"""Security tools for admin verification."""

from typing import Any


def get_security_tools() -> list[dict[str, Any]]:
    """Get security tools for admin verification."""
    return [
        {
            "name": "check_username_spoofing",
            "description": (
                "Проверить username на попытку маскировки под админа."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "@username",
                    },
                    "telegram_id": {
                        "type": "integer",
                        "description": "Telegram ID (опционально)",
                    },
                },
                "required": ["username"],
            },
        },
        {
            "name": "get_verified_admins",
            "description": "Получить список верифицированных админов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "verify_admin_identity",
            "description": (
                "Проверить личность админа по telegram_id."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "telegram_id": {
                        "type": "integer",
                        "description": "Telegram ID",
                    },
                    "username": {
                        "type": "string",
                        "description": "@username (опционально)",
                    },
                },
                "required": ["telegram_id"],
            },
        },
    ]
