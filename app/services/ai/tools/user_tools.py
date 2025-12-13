"""User management tools."""

from typing import Any


def get_user_management_tools() -> list[dict[str, Any]]:
    """Get user management tools."""
    return [
        {
            "name": "get_user_profile",
            "description": "Получить полный профиль пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": (
                            "@username, telegram_id или wallet"
                        ),
                    },
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "search_users",
            "description": "Поиск пользователей.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Максимум результатов",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "change_user_balance",
            "description": (
                "Изменить доступный баланс пользователя (НЕ депозиты). "
                "Выполнять только по явной команде админа с причиной."
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
                        "description": "Сумма изменения",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина изменения",
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract"],
                        "description": "Операция",
                    },
                },
                "required": [
                    "user_identifier",
                    "amount",
                    "reason",
                    "operation",
                ],
            },
        },
        {
            "name": "block_user",
            "description": "Заблокировать пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина блокировки",
                    },
                },
                "required": ["user_identifier", "reason"],
            },
        },
        {
            "name": "unblock_user",
            "description": "Разблокировать пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "get_user_deposits",
            "description": "Получить депозиты пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "get_users_stats",
            "description": "Получить статистику пользователей.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]


def get_user_wallet_tools() -> list[dict[str, Any]]:
    """Get wallet tools for regular users (limited)."""
    return [
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
                        "description": "Telegram ID",
                    },
                },
                "required": ["user_telegram_id"],
            },
        },
    ]
