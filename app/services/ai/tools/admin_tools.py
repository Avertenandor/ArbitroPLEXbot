"""System administration and admin management tools."""

from typing import Any


def get_system_admin_tools() -> list[dict[str, Any]]:
    """Get system administration tools (only for super admin)."""
    return [
        {
            "name": "get_emergency_status",
            "description": "Получить статус аварийных стопов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "emergency_full_stop",
            "description": (
                "ПОЛНАЯ ОСТАНОВКА всех операций! ТОЛЬКО для Командира!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "emergency_full_resume",
            "description": (
                "Возобновить все операции после полной остановки."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "toggle_emergency_deposits",
            "description": "Вкл/выкл приём депозитов.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "enable_stop": {
                        "type": "boolean",
                        "description": "True = остановить",
                    },
                },
                "required": ["enable_stop"],
            },
        },
        {
            "name": "toggle_emergency_withdrawals",
            "description": "Вкл/выкл выводы.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "enable_stop": {
                        "type": "boolean",
                        "description": "True = остановить",
                    },
                },
                "required": ["enable_stop"],
            },
        },
        {
            "name": "toggle_emergency_roi",
            "description": "Вкл/выкл начисление ROI.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "enable_stop": {
                        "type": "boolean",
                        "description": "True = остановить",
                    },
                },
                "required": ["enable_stop"],
            },
        },
        {
            "name": "get_blockchain_status",
            "description": "Получить статус блокчейн провайдеров.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "switch_rpc_provider",
            "description": "Переключить RPC провайдер.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["quicknode", "nodereal", "nodereal2"],
                        "description": "Провайдер",
                    },
                },
                "required": ["provider"],
            },
        },
        {
            "name": "toggle_rpc_auto_switch",
            "description": "Вкл/выкл авто-переключение RPC.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "enable": {
                        "type": "boolean",
                        "description": "True = включить",
                    },
                },
                "required": ["enable"],
            },
        },
        {
            "name": "get_platform_health",
            "description": "Получить здоровье платформы.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_global_settings",
            "description": "Получить глобальные настройки.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]


def get_admin_management_tools() -> list[dict[str, Any]]:
    """Get admin management tools (only for super admin)."""
    return [
        {
            "name": "get_admins_list",
            "description": "Получить список всех администраторов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_admin_details",
            "description": "Получить детали конкретного админа.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                },
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "block_admin",
            "description": (
                "Заблокировать администратора. ТОЛЬКО ДЛЯ КОМАНДИРА!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина блокировки",
                    },
                },
                "required": ["admin_identifier", "reason"],
            },
        },
        {
            "name": "unblock_admin",
            "description": (
                "Разблокировать администратора. ТОЛЬКО ДЛЯ КОМАНДИРА!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                },
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "change_admin_role",
            "description": (
                "Изменить роль администратора. ТОЛЬКО ДЛЯ КОМАНДИРА!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id",
                    },
                    "new_role": {
                        "type": "string",
                        "enum": ["admin", "support"],
                        "description": "Новая роль",
                    },
                },
                "required": ["admin_identifier", "new_role"],
            },
        },
        {
            "name": "get_admin_stats",
            "description": "Получить статистику по администраторам.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]
