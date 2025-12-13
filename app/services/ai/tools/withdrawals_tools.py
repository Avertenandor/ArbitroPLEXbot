"""Withdrawal management tools."""

from typing import Any


def get_withdrawals_tools() -> list[dict[str, Any]]:
    """Get withdrawal management tools."""
    return [
        {
            "name": "get_pending_withdrawals",
            "description": "Получить список ожидающих выводов.",
            "input_schema": {
                "type": "object",
                "properties": {
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
            "name": "get_withdrawal_details",
            "description": "Получить детали заявки на вывод.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "withdrawal_id": {
                        "type": "integer",
                        "description": "ID заявки",
                    },
                },
                "required": ["withdrawal_id"],
            },
        },
        {
            "name": "approve_withdrawal",
            "description": "Одобрить вывод. ТОЛЬКО доверенные админы!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "withdrawal_id": {
                        "type": "integer",
                        "description": "ID заявки",
                    },
                    "tx_hash": {
                        "type": "string",
                        "description": "Хеш транзакции (опционально)",
                    },
                },
                "required": ["withdrawal_id"],
            },
        },
        {
            "name": "reject_withdrawal",
            "description": (
                "Отклонить вывод с возвратом на баланс. ТОЛЬКО "
                "доверенные админы!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "withdrawal_id": {
                        "type": "integer",
                        "description": "ID заявки",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина отклонения",
                    },
                },
                "required": ["withdrawal_id", "reason"],
            },
        },
        {
            "name": "get_withdrawals_statistics",
            "description": "Получить статистику выводов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]
