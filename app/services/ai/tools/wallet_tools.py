"""Wallet balance tools."""

from typing import Any


def get_wallet_tools() -> list[dict[str, Any]]:
    """Get wallet balance tools."""
    return [
        {
            "name": "check_user_wallet",
            "description": (
                "Проверить балансы кошелька пользователя "
                "(BNB, USDT, PLEX)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": (
                            "@username, telegram_id или wallet (0x...)"
                        ),
                    },
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "get_plex_rate",
            "description": "Получить текущий курс PLEX токена.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_wallet_summary_for_dialog",
            "description": (
                "Получить сводку кошелька для завершения диалога."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_telegram_id": {
                        "type": "integer",
                        "description": "Telegram ID пользователя",
                    },
                },
                "required": ["user_telegram_id"],
            },
        },
    ]
