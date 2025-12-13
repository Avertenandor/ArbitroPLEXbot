"""Deposit management tools."""

from typing import Any


def get_deposits_tools() -> list[dict[str, Any]]:
    """Get deposit management tools."""
    return [
        {
            "name": "get_deposit_levels_config",
            "description": "Получить конфигурацию уровней депозитов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_user_deposits_list",
            "description": "Получить список депозитов пользователя.",
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
            "name": "get_pending_deposits",
            "description": "Получить список ожидающих депозитов.",
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
            "name": "get_deposit_details",
            "description": "Получить детали депозита по ID.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "deposit_id": {
                        "type": "integer",
                        "description": "ID депозита",
                    },
                },
                "required": ["deposit_id"],
            },
        },
        {
            "name": "get_platform_deposit_stats",
            "description": "Получить статистику депозитов платформы.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "change_max_deposit_level",
            "description": (
                "Изменить максимальный уровень депозитов. ТОЛЬКО "
                "ДОВЕРЕННЫЕ АДМИНЫ!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "new_max": {
                        "type": "integer",
                        "description": "Новый макс. уровень (1-5)",
                    },
                },
                "required": ["new_max"],
            },
        },
        {
            "name": "create_manual_deposit",
            "description": (
                "Создать ручной депозит. Выполнять только по явной "
                "команде админа с причиной."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                    "level": {
                        "type": "integer",
                        "description": "Уровень (1-5)",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Сумма в USDT",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина создания",
                    },
                },
                "required": ["user_identifier", "level", "amount", "reason"],
            },
        },
        {
            "name": "modify_deposit_roi",
            "description": (
                "Изменить ROI параметры депозита. ТОЛЬКО ДОВЕРЕННЫЕ "
                "АДМИНЫ!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "deposit_id": {
                        "type": "integer",
                        "description": "ID депозита",
                    },
                    "new_roi_paid": {
                        "type": "number",
                        "description": "Новая сумма выплаченного ROI",
                    },
                    "new_roi_cap": {
                        "type": "number",
                        "description": "Новый ROI cap",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина изменения",
                    },
                },
                "required": ["deposit_id", "reason"],
            },
        },
        {
            "name": "cancel_deposit",
            "description": (
                "Отменить депозит (исключить из учёта). Выполнять только "
                "по явной команде админа с причиной."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "deposit_id": {
                        "type": "integer",
                        "description": "ID депозита",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина отмены",
                    },
                },
                "required": ["deposit_id", "reason"],
            },
        },
        {
            "name": "confirm_deposit",
            "description": (
                "Подтвердить pending депозит вручную. ТОЛЬКО ДОВЕРЕННЫЕ "
                "АДМИНЫ!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "deposit_id": {
                        "type": "integer",
                        "description": "ID депозита",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина/заметки",
                    },
                },
                "required": ["deposit_id"],
            },
        },
    ]
