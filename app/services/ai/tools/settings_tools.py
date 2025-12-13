"""Platform settings tools."""

from typing import Any


def get_settings_tools() -> list[dict[str, Any]]:
    """Get platform settings tools."""
    return [
        {
            "name": "get_withdrawal_settings",
            "description": "Получить настройки выводов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "set_min_withdrawal",
            "description": "Установить минимальную сумму вывода.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Сумма в USDT (0.1-1000)",
                    },
                },
                "required": ["amount"],
            },
        },
        {
            "name": "toggle_daily_limit",
            "description": "Включить/выключить дневной лимит вывода.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "True = включить",
                    },
                },
                "required": ["enabled"],
            },
        },
        {
            "name": "set_daily_limit",
            "description": "Установить сумму дневного лимита вывода.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Сумма в USDT (мин. 10)",
                    },
                },
                "required": ["amount"],
            },
        },
        {
            "name": "toggle_auto_withdrawal",
            "description": "Включить/выключить автоматический вывод.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "True = включить",
                    },
                },
                "required": ["enabled"],
            },
        },
        {
            "name": "set_service_fee",
            "description": "Установить комиссию сервиса для выводов.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "fee": {
                        "type": "number",
                        "description": "Процент комиссии (0-50)",
                    },
                },
                "required": ["fee"],
            },
        },
        {
            "name": "get_deposit_settings",
            "description": "Получить настройки уровней депозитов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "set_level_corridor",
            "description": "Установить коридор для уровня депозита.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "level_type": {
                        "type": "string",
                        "enum": [
                            "test",
                            "level_1",
                            "level_2",
                            "level_3",
                            "level_4",
                            "level_5",
                        ],
                        "description": "Тип уровня",
                    },
                    "min_amount": {
                        "type": "number",
                        "description": "Мин. сумма",
                    },
                    "max_amount": {
                        "type": "number",
                        "description": "Макс. сумма",
                    },
                },
                "required": ["level_type", "min_amount", "max_amount"],
            },
        },
        {
            "name": "toggle_deposit_level",
            "description": "Включить/отключить уровень депозита.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "level_type": {
                        "type": "string",
                        "enum": [
                            "test",
                            "level_1",
                            "level_2",
                            "level_3",
                            "level_4",
                            "level_5",
                        ],
                        "description": "Тип уровня",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "True = включить",
                    },
                },
                "required": ["level_type", "enabled"],
            },
        },
        {
            "name": "set_plex_rate",
            "description": (
                "Установить PLEX за $1 для всех уровней."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "rate": {
                        "type": "number",
                        "description": "PLEX за 1$ (1-100)",
                    },
                },
                "required": ["rate"],
            },
        },
        {
            "name": "get_scheduled_tasks",
            "description": "Получить список запланированных задач.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "trigger_task",
            "description": "Запустить задачу вручную.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "enum": [
                            "balance_notifications",
                            "plex_balance_monitor",
                            "daily_rewards",
                            "deposit_monitoring",
                            "blockchain_cache_sync",
                            "notification_retry",
                        ],
                        "description": "ID задачи",
                    },
                },
                "required": ["task_id"],
            },
        },
        {
            "name": "create_admin",
            "description": (
                "Создать нового администратора. ТОЛЬКО КОМАНДИР!"
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
                        "description": "@username",
                    },
                    "role": {
                        "type": "string",
                        "enum": ["moderator", "admin", "extended_admin"],
                        "description": "Роль",
                    },
                },
                "required": ["telegram_id", "role"],
            },
        },
        {
            "name": "delete_admin",
            "description": "Удалить администратора. ТОЛЬКО КОМАНДИР!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "telegram_id": {
                        "type": "integer",
                        "description": "Telegram ID",
                    },
                },
                "required": ["telegram_id"],
            },
        },
    ]
