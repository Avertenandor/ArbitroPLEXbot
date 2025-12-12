"""
AI Tool Definitions.

Contains all tool definitions for AI assistant,
organized by category for better maintainability.
"""

from typing import Any

from app.services.ai.prompts import UserRole


def get_messaging_tools(role: UserRole = UserRole.SUPER_ADMIN) -> list[dict[str, Any]]:
    """Get messaging and broadcast tools based on role."""
    is_commander = role == UserRole.SUPER_ADMIN

    if is_commander:
        broadcast_groups = ["active_appeals", "active_deposits", "active_24h", "active_7d", "all"]
        default_limit = 100
    else:
        broadcast_groups = ["active_appeals", "active_deposits", "active_24h", "active_7d"]
        default_limit = 50

    return [
        {
            "name": "send_message_to_user",
            "description": "Отправить персональное сообщение конкретному пользователю.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {
                        "type": "string",
                        "description": "@username, telegram_id или ID:xxx пользователя",
                    },
                    "message_text": {"type": "string", "description": "Текст сообщения (поддерживается Markdown)"},
                },
                "required": ["user_identifier", "message_text"],
            },
        },
        {
            "name": "broadcast_to_group",
            "description": f"Массовая рассылка сообщения группе пользователей.{' Лимит: ' + str(default_limit) + ' получателей.' if not is_commander else ''}",
            "input_schema": {
                "type": "object",
                "properties": {
                    "group": {
                        "type": "string",
                        "enum": broadcast_groups,
                        "description": "Группа получателей" + (", all (все)" if is_commander else ""),
                    },
                    "message_text": {"type": "string", "description": "Текст сообщения (Markdown)"},
                    "limit": {
                        "type": "integer",
                        "description": f"Максимум получателей (по умолчанию {default_limit})",
                        "default": default_limit,
                    },
                },
                "required": ["group", "message_text"],
            },
        },
        {
            "name": "get_users_list",
            "description": "Получить список пользователей группы.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "group": {"type": "string", "enum": broadcast_groups, "description": "Группа пользователей"},
                    "limit": {"type": "integer", "description": "Максимум записей", "default": 20},
                },
                "required": ["group"],
            },
        },
        {
            "name": "invite_to_dialog",
            "description": "Отправить персональное приглашение к диалогу с Арьей.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "custom_message": {"type": "string", "description": "Кастомный текст (опционально)"},
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "mass_invite_to_dialog",
            "description": f"Массовая рассылка приглашений к диалогу.{' Лимит: ' + str(default_limit) + '.' if not is_commander else ''}",
            "input_schema": {
                "type": "object",
                "properties": {
                    "group": {
                        "type": "string",
                        "enum": ["active_appeals", "active_deposits", "active_24h", "active_7d"],
                        "description": "Группа пользователей",
                    },
                    "custom_message": {"type": "string", "description": "Кастомный текст"},
                    "limit": {
                        "type": "integer",
                        "description": f"Максимум приглашений (по умолчанию {default_limit})",
                        "default": default_limit,
                    },
                },
                "required": ["group"],
            },
        },
        {
            "name": "send_feedback_request",
            "description": "Отправить запрос обратной связи админу. Спросить о предложениях, проблемах или идеях по улучшению.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {
                        "type": "string",
                        "description": "@username или telegram_id админа",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Тема опроса (например: 'улучшения бота', 'проблемы', 'новые функции')",
                    },
                    "question": {
                        "type": "string",
                        "description": "Конкретный вопрос для админа",
                    },
                },
                "required": ["admin_identifier", "topic", "question"],
            },
        },
        {
            "name": "broadcast_to_admins",
            "description": "Отправить сообщение всем активным админам. Для объявлений, опросов или сбора обратной связи.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message_text": {
                        "type": "string",
                        "description": "Текст сообщения (Markdown)",
                    },
                    "request_feedback": {
                        "type": "boolean",
                        "description": "Добавить кнопку 'Ответить ARIA'",
                        "default": True,
                    },
                },
                "required": ["message_text"],
            },
        },
    ]


def get_interview_tools() -> list[dict[str, Any]]:
    """Get interview tools for conducting interviews with admins."""
    return [
        {
            "name": "start_interview",
            "description": "Начать интервью с админом. Отправляет вопросы по одному.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {"type": "string", "description": "@username или telegram_id админа"},
                    "topic": {"type": "string", "description": "Тема интервью"},
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Список вопросов (1-10)",
                    },
                },
                "required": ["admin_identifier", "topic", "questions"],
            },
        },
        {
            "name": "get_interview_status",
            "description": "Получить статус активного интервью.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {"type": "string", "description": "@username или telegram_id"},
                },
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "cancel_interview",
            "description": "Отменить активное интервью.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {"type": "string", "description": "@username или telegram_id"},
                },
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "get_knowledge_by_user",
            "description": "Получить записи базы знаний от конкретного пользователя/админа. Показывает интервью и записи.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "@username пользователя (без @)"},
                },
                "required": ["username"],
            },
        },
    ]


def get_bonus_tools() -> list[dict[str, Any]]:
    """Get bonus management tools."""
    return [
        {
            "name": "grant_bonus",
            "description": "Начислить бонус пользователю. ВАЖНО: только по явной команде админа!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "amount": {"type": "number", "description": "Сумма бонуса в USDT (1-10000)"},
                    "reason": {"type": "string", "description": "Причина начисления"},
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
                    "user_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "active_only": {"type": "boolean", "description": "Только активные", "default": False},
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "cancel_bonus",
            "description": "Отменить активный бонус. ВАЖНО: только по явной команде админа!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "bonus_id": {"type": "integer", "description": "ID бонуса"},
                    "reason": {"type": "string", "description": "Причина отмены"},
                },
                "required": ["bonus_id", "reason"],
            },
        },
    ]


def get_appeals_tools() -> list[dict[str, Any]]:
    """Get appeals management tools."""
    return [
        {
            "name": "get_appeals_list",
            "description": "Получить список обращений пользователей.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "under_review", "approved", "rejected"],
                        "description": "Фильтр по статусу",
                    },
                    "limit": {"type": "integer", "description": "Максимум записей", "default": 20},
                },
                "required": [],
            },
        },
        {
            "name": "get_appeal_details",
            "description": "Получить детали обращения по ID.",
            "input_schema": {
                "type": "object",
                "properties": {"appeal_id": {"type": "integer", "description": "ID обращения"}},
                "required": ["appeal_id"],
            },
        },
        {
            "name": "take_appeal",
            "description": "Взять обращение на рассмотрение. ТОЛЬКО по команде админа!",
            "input_schema": {
                "type": "object",
                "properties": {"appeal_id": {"type": "integer", "description": "ID обращения"}},
                "required": ["appeal_id"],
            },
        },
        {
            "name": "resolve_appeal",
            "description": "Закрыть обращение с решением. ТОЛЬКО по команде админа!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "appeal_id": {"type": "integer", "description": "ID обращения"},
                    "decision": {"type": "string", "enum": ["approve", "reject"], "description": "Решение"},
                    "notes": {"type": "string", "description": "Комментарий"},
                },
                "required": ["appeal_id", "decision"],
            },
        },
        {
            "name": "reply_to_appeal",
            "description": "Отправить ответ пользователю по обращению.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "appeal_id": {"type": "integer", "description": "ID обращения"},
                    "message": {"type": "string", "description": "Текст ответа"},
                },
                "required": ["appeal_id", "message"],
            },
        },
    ]


def get_inquiries_tools() -> list[dict[str, Any]]:
    """Get user inquiries management tools."""
    return [
        {
            "name": "get_inquiries_list",
            "description": "Получить список обращений пользователей.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["new", "in_progress", "closed"],
                        "description": "Фильтр по статусу",
                    },
                    "limit": {"type": "integer", "description": "Максимум записей", "default": 20},
                },
                "required": [],
            },
        },
        {
            "name": "get_inquiry_details",
            "description": "Получить детали обращения с перепиской.",
            "input_schema": {
                "type": "object",
                "properties": {"inquiry_id": {"type": "integer", "description": "ID обращения"}},
                "required": ["inquiry_id"],
            },
        },
        {
            "name": "take_inquiry",
            "description": "Взять обращение в работу.",
            "input_schema": {
                "type": "object",
                "properties": {"inquiry_id": {"type": "integer", "description": "ID обращения"}},
                "required": ["inquiry_id"],
            },
        },
        {
            "name": "reply_to_inquiry",
            "description": "Ответить на обращение пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "inquiry_id": {"type": "integer", "description": "ID обращения"},
                    "message": {"type": "string", "description": "Текст ответа"},
                },
                "required": ["inquiry_id", "message"],
            },
        },
        {
            "name": "close_inquiry",
            "description": "Закрыть обращение.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "inquiry_id": {"type": "integer", "description": "ID обращения"},
                    "reason": {"type": "string", "description": "Причина закрытия"},
                },
                "required": ["inquiry_id"],
            },
        },
    ]


def get_user_management_tools() -> list[dict[str, Any]]:
    """Get user management tools."""
    return [
        {
            "name": "get_user_profile",
            "description": "Получить полный профиль пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "@username, telegram_id или wallet"},
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
                    "query": {"type": "string", "description": "Поисковый запрос"},
                    "limit": {"type": "integer", "description": "Максимум результатов", "default": 20},
                },
                "required": ["query"],
            },
        },
        {
            "name": "change_user_balance",
            "description": "Изменить доступный баланс пользователя (НЕ депозиты). Выполнять только по явной команде админа с причиной.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "amount": {"type": "number", "description": "Сумма изменения"},
                    "reason": {"type": "string", "description": "Причина изменения"},
                    "operation": {"type": "string", "enum": ["add", "subtract"], "description": "Операция"},
                },
                "required": ["user_identifier", "amount", "reason", "operation"],
            },
        },
        {
            "name": "block_user",
            "description": "Заблокировать пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "reason": {"type": "string", "description": "Причина блокировки"},
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
                    "user_identifier": {"type": "string", "description": "@username или telegram_id"},
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
                    "user_identifier": {"type": "string", "description": "@username или telegram_id"},
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "get_users_stats",
            "description": "Получить статистику пользователей.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def get_statistics_tools() -> list[dict[str, Any]]:
    """Get platform statistics tools."""
    return [
        {
            "name": "get_deposit_stats",
            "description": "Получить статистику депозитов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_bonus_stats",
            "description": "Получить статистику бонусов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_withdrawal_stats",
            "description": "Получить статистику выводов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_financial_report",
            "description": "Получить финансовый отчёт.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_roi_stats",
            "description": "Получить статистику ROI.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def get_withdrawals_tools() -> list[dict[str, Any]]:
    """Get withdrawal management tools."""
    return [
        {
            "name": "get_pending_withdrawals",
            "description": "Получить список ожидающих выводов.",
            "input_schema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Максимум записей", "default": 20}},
                "required": [],
            },
        },
        {
            "name": "get_withdrawal_details",
            "description": "Получить детали заявки на вывод.",
            "input_schema": {
                "type": "object",
                "properties": {"withdrawal_id": {"type": "integer", "description": "ID заявки"}},
                "required": ["withdrawal_id"],
            },
        },
        {
            "name": "approve_withdrawal",
            "description": "Одобрить вывод. ТОЛЬКО доверенные админы!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "withdrawal_id": {"type": "integer", "description": "ID заявки"},
                    "tx_hash": {"type": "string", "description": "Хеш транзакции (опционально)"},
                },
                "required": ["withdrawal_id"],
            },
        },
        {
            "name": "reject_withdrawal",
            "description": "Отклонить вывод с возвратом на баланс. ТОЛЬКО доверенные админы!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "withdrawal_id": {"type": "integer", "description": "ID заявки"},
                    "reason": {"type": "string", "description": "Причина отклонения"},
                },
                "required": ["withdrawal_id", "reason"],
            },
        },
        {
            "name": "get_withdrawals_statistics",
            "description": "Получить статистику выводов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def get_system_admin_tools() -> list[dict[str, Any]]:
    """Get system administration tools (only for super admin)."""
    return [
        {
            "name": "get_emergency_status",
            "description": "Получить статус аварийных стопов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "emergency_full_stop",
            "description": "ПОЛНАЯ ОСТАНОВКА всех операций! ТОЛЬКО для Командира!",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "emergency_full_resume",
            "description": "Возобновить все операции после полной остановки.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "toggle_emergency_deposits",
            "description": "Вкл/выкл приём депозитов.",
            "input_schema": {
                "type": "object",
                "properties": {"enable_stop": {"type": "boolean", "description": "True = остановить"}},
                "required": ["enable_stop"],
            },
        },
        {
            "name": "toggle_emergency_withdrawals",
            "description": "Вкл/выкл выводы.",
            "input_schema": {
                "type": "object",
                "properties": {"enable_stop": {"type": "boolean", "description": "True = остановить"}},
                "required": ["enable_stop"],
            },
        },
        {
            "name": "toggle_emergency_roi",
            "description": "Вкл/выкл начисление ROI.",
            "input_schema": {
                "type": "object",
                "properties": {"enable_stop": {"type": "boolean", "description": "True = остановить"}},
                "required": ["enable_stop"],
            },
        },
        {
            "name": "get_blockchain_status",
            "description": "Получить статус блокчейн провайдеров.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
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
                    }
                },
                "required": ["provider"],
            },
        },
        {
            "name": "toggle_rpc_auto_switch",
            "description": "Вкл/выкл авто-переключение RPC.",
            "input_schema": {
                "type": "object",
                "properties": {"enable": {"type": "boolean", "description": "True = включить"}},
                "required": ["enable"],
            },
        },
        {
            "name": "get_platform_health",
            "description": "Получить здоровье платформы.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_global_settings",
            "description": "Получить глобальные настройки.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def get_admin_management_tools() -> list[dict[str, Any]]:
    """Get admin management tools (only for super admin)."""
    return [
        {
            "name": "get_admins_list",
            "description": "Получить список всех администраторов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_admin_details",
            "description": "Получить детали конкретного админа.",
            "input_schema": {
                "type": "object",
                "properties": {"admin_identifier": {"type": "string", "description": "@username или telegram_id"}},
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "block_admin",
            "description": "Заблокировать администратора. ТОЛЬКО ДЛЯ КОМАНДИРА!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "reason": {"type": "string", "description": "Причина блокировки"},
                },
                "required": ["admin_identifier", "reason"],
            },
        },
        {
            "name": "unblock_admin",
            "description": "Разблокировать администратора. ТОЛЬКО ДЛЯ КОМАНДИРА!",
            "input_schema": {
                "type": "object",
                "properties": {"admin_identifier": {"type": "string", "description": "@username или telegram_id"}},
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "change_admin_role",
            "description": "Изменить роль администратора. ТОЛЬКО ДЛЯ КОМАНДИРА!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "new_role": {"type": "string", "enum": ["admin", "support"], "description": "Новая роль"},
                },
                "required": ["admin_identifier", "new_role"],
            },
        },
        {
            "name": "get_admin_stats",
            "description": "Получить статистику по администраторам.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def get_deposits_tools() -> list[dict[str, Any]]:
    """Get deposit management tools."""
    return [
        {
            "name": "get_deposit_levels_config",
            "description": "Получить конфигурацию уровней депозитов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_user_deposits_list",
            "description": "Получить список депозитов пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {"user_identifier": {"type": "string", "description": "@username или telegram_id"}},
                "required": ["user_identifier"],
            },
        },
        {
            "name": "get_pending_deposits",
            "description": "Получить список ожидающих депозитов.",
            "input_schema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Макс. кол-во"}},
                "required": [],
            },
        },
        {
            "name": "get_deposit_details",
            "description": "Получить детали депозита по ID.",
            "input_schema": {
                "type": "object",
                "properties": {"deposit_id": {"type": "integer", "description": "ID депозита"}},
                "required": ["deposit_id"],
            },
        },
        {
            "name": "get_platform_deposit_stats",
            "description": "Получить статистику депозитов платформы.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "change_max_deposit_level",
            "description": "Изменить максимальный уровень депозитов. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!",
            "input_schema": {
                "type": "object",
                "properties": {"new_max": {"type": "integer", "description": "Новый макс. уровень (1-5)"}},
                "required": ["new_max"],
            },
        },
        {
            "name": "create_manual_deposit",
            "description": "Создать ручной депозит. Выполнять только по явной команде админа с причиной.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "level": {"type": "integer", "description": "Уровень (1-5)"},
                    "amount": {"type": "number", "description": "Сумма в USDT"},
                    "reason": {"type": "string", "description": "Причина создания"},
                },
                "required": ["user_identifier", "level", "amount", "reason"],
            },
        },
        {
            "name": "modify_deposit_roi",
            "description": "Изменить ROI параметры депозита. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "deposit_id": {"type": "integer", "description": "ID депозита"},
                    "new_roi_paid": {"type": "number", "description": "Новая сумма выплаченного ROI"},
                    "new_roi_cap": {"type": "number", "description": "Новый ROI cap"},
                    "reason": {"type": "string", "description": "Причина изменения"},
                },
                "required": ["deposit_id", "reason"],
            },
        },
        {
            "name": "cancel_deposit",
            "description": "Отменить депозит (исключить из учёта). Выполнять только по явной команде админа с причиной.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "deposit_id": {"type": "integer", "description": "ID депозита"},
                    "reason": {"type": "string", "description": "Причина отмены"},
                },
                "required": ["deposit_id", "reason"],
            },
        },
        {
            "name": "confirm_deposit",
            "description": "Подтвердить pending депозит вручную. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "deposit_id": {"type": "integer", "description": "ID депозита"},
                    "reason": {"type": "string", "description": "Причина/заметки"},
                },
                "required": ["deposit_id"],
            },
        },
    ]


def get_roi_tools() -> list[dict[str, Any]]:
    """Get ROI corridor tools."""
    return [
        {
            "name": "get_roi_config",
            "description": "Получить конфигурацию ROI коридора.",
            "input_schema": {
                "type": "object",
                "properties": {"level": {"type": "integer", "description": "Уровень (1-5) или пусто для всех"}},
                "required": [],
            },
        },
        {
            "name": "set_roi_corridor",
            "description": "Установить ROI коридор для уровня. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Уровень (1-5)"},
                    "mode": {"type": "string", "enum": ["custom", "equal"], "description": "Режим"},
                    "roi_min": {"type": "number", "description": "Мин. ROI %"},
                    "roi_max": {"type": "number", "description": "Макс. ROI %"},
                    "roi_fixed": {"type": "number", "description": "Фикс. ROI %"},
                    "reason": {"type": "string", "description": "Причина изменения"},
                },
                "required": ["level", "mode"],
            },
        },
        {
            "name": "get_corridor_history",
            "description": "Получить историю изменений ROI коридора.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Уровень (1-5)"},
                    "limit": {"type": "integer", "description": "Макс. кол-во записей"},
                },
                "required": [],
            },
        },
    ]


def get_blacklist_tools() -> list[dict[str, Any]]:
    """Get blacklist management tools."""
    return [
        {
            "name": "get_blacklist",
            "description": "Получить чёрный список.",
            "input_schema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Макс. кол-во"}},
                "required": [],
            },
        },
        {
            "name": "check_blacklist",
            "description": "Проверить наличие в чёрном списке.",
            "input_schema": {
                "type": "object",
                "properties": {"identifier": {"type": "string", "description": "@username, telegram_id или wallet"}},
                "required": ["identifier"],
            },
        },
        {
            "name": "add_to_blacklist",
            "description": "Добавить в чёрный список. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "@username, telegram_id или wallet"},
                    "reason": {"type": "string", "description": "Причина"},
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
            "description": "Удалить из чёрного списка. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "@username, telegram_id или wallet"},
                    "reason": {"type": "string", "description": "Причина удаления"},
                },
                "required": ["identifier", "reason"],
            },
        },
    ]


def get_finpass_tools() -> list[dict[str, Any]]:
    """Get financial password recovery tools."""
    return [
        {
            "name": "get_finpass_requests",
            "description": "Получить заявки на восстановление финпароля.",
            "input_schema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Макс. кол-во"}},
                "required": [],
            },
        },
        {
            "name": "get_finpass_request_details",
            "description": "Получить детали заявки на восстановление.",
            "input_schema": {
                "type": "object",
                "properties": {"request_id": {"type": "integer", "description": "ID заявки"}},
                "required": ["request_id"],
            },
        },
        {
            "name": "approve_finpass_request",
            "description": "Одобрить заявку. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "integer", "description": "ID заявки"},
                    "notes": {"type": "string", "description": "Заметки"},
                },
                "required": ["request_id"],
            },
        },
        {
            "name": "reject_finpass_request",
            "description": "Отклонить заявку. ТОЛЬКО ДОВЕРЕННЫЕ АДМИНЫ!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "integer", "description": "ID заявки"},
                    "reason": {"type": "string", "description": "Причина отклонения"},
                },
                "required": ["request_id", "reason"],
            },
        },
        {
            "name": "get_finpass_stats",
            "description": "Получить статистику заявок.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def get_wallet_tools() -> list[dict[str, Any]]:
    """Get wallet balance tools."""
    return [
        {
            "name": "check_user_wallet",
            "description": "Проверить балансы кошелька пользователя (BNB, USDT, PLEX).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "@username, telegram_id или wallet (0x...)"},
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "get_plex_rate",
            "description": "Получить текущий курс PLEX токена.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_wallet_summary_for_dialog",
            "description": "Получить сводку кошелька для завершения диалога.",
            "input_schema": {
                "type": "object",
                "properties": {"user_telegram_id": {"type": "integer", "description": "Telegram ID пользователя"}},
                "required": ["user_telegram_id"],
            },
        },
    ]


def get_referral_tools() -> list[dict[str, Any]]:
    """Get referral statistics tools."""
    return [
        {
            "name": "get_platform_referral_stats",
            "description": "Получить реферальную статистику платформы.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_user_referrals",
            "description": "Получить рефералов пользователя.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "limit": {"type": "integer", "description": "Макс. кол-во"},
                },
                "required": ["user_identifier"],
            },
        },
        {
            "name": "get_top_referrers",
            "description": "Получить топ рефереров по кол-ву приглашённых.",
            "input_schema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Кол-во в топе"}},
                "required": [],
            },
        },
        {
            "name": "get_top_earners",
            "description": "Получить топ рефереров по заработку.",
            "input_schema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Кол-во в топе"}},
                "required": [],
            },
        },
    ]


def get_logs_tools() -> list[dict[str, Any]]:
    """Get admin logs tools."""
    return [
        {
            "name": "get_recent_logs",
            "description": "Получить последние действия админов.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Кол-во записей"},
                    "action_type": {"type": "string", "description": "Фильтр по типу"},
                },
                "required": [],
            },
        },
        {
            "name": "get_admin_activity",
            "description": "Получить активность конкретного админа.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "admin_identifier": {"type": "string", "description": "@username или telegram_id"},
                    "limit": {"type": "integer", "description": "Кол-во записей"},
                },
                "required": ["admin_identifier"],
            },
        },
        {
            "name": "search_logs",
            "description": "Поиск в логах действий.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "ID целевого пользователя"},
                    "action_type": {"type": "string", "description": "Тип действия"},
                    "limit": {"type": "integer", "description": "Кол-во записей"},
                },
                "required": [],
            },
        },
        {
            "name": "get_action_types_stats",
            "description": "Получить статистику типов действий.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def get_settings_tools() -> list[dict[str, Any]]:
    """Get platform settings tools."""
    return [
        {
            "name": "get_withdrawal_settings",
            "description": "Получить настройки выводов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "set_min_withdrawal",
            "description": "Установить минимальную сумму вывода.",
            "input_schema": {
                "type": "object",
                "properties": {"amount": {"type": "number", "description": "Сумма в USDT (0.1-1000)"}},
                "required": ["amount"],
            },
        },
        {
            "name": "toggle_daily_limit",
            "description": "Включить/выключить дневной лимит вывода.",
            "input_schema": {
                "type": "object",
                "properties": {"enabled": {"type": "boolean", "description": "True = включить"}},
                "required": ["enabled"],
            },
        },
        {
            "name": "set_daily_limit",
            "description": "Установить сумму дневного лимита вывода.",
            "input_schema": {
                "type": "object",
                "properties": {"amount": {"type": "number", "description": "Сумма в USDT (мин. 10)"}},
                "required": ["amount"],
            },
        },
        {
            "name": "toggle_auto_withdrawal",
            "description": "Включить/выключить автоматический вывод.",
            "input_schema": {
                "type": "object",
                "properties": {"enabled": {"type": "boolean", "description": "True = включить"}},
                "required": ["enabled"],
            },
        },
        {
            "name": "set_service_fee",
            "description": "Установить комиссию сервиса для выводов.",
            "input_schema": {
                "type": "object",
                "properties": {"fee": {"type": "number", "description": "Процент комиссии (0-50)"}},
                "required": ["fee"],
            },
        },
        {
            "name": "get_deposit_settings",
            "description": "Получить настройки уровней депозитов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "set_level_corridor",
            "description": "Установить коридор для уровня депозита.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "level_type": {
                        "type": "string",
                        "enum": ["test", "level_1", "level_2", "level_3", "level_4", "level_5"],
                        "description": "Тип уровня",
                    },
                    "min_amount": {"type": "number", "description": "Мин. сумма"},
                    "max_amount": {"type": "number", "description": "Макс. сумма"},
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
                        "enum": ["test", "level_1", "level_2", "level_3", "level_4", "level_5"],
                        "description": "Тип уровня",
                    },
                    "enabled": {"type": "boolean", "description": "True = включить"},
                },
                "required": ["level_type", "enabled"],
            },
        },
        {
            "name": "set_plex_rate",
            "description": "Установить PLEX за $1 для всех уровней.",
            "input_schema": {
                "type": "object",
                "properties": {"rate": {"type": "number", "description": "PLEX за 1$ (1-100)"}},
                "required": ["rate"],
            },
        },
        {
            "name": "get_scheduled_tasks",
            "description": "Получить список запланированных задач.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
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
                    }
                },
                "required": ["task_id"],
            },
        },
        {
            "name": "create_admin",
            "description": "Создать нового администратора. ТОЛЬКО КОМАНДИР!",
            "input_schema": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "integer", "description": "Telegram ID"},
                    "username": {"type": "string", "description": "@username"},
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
                "properties": {"telegram_id": {"type": "integer", "description": "Telegram ID"}},
                "required": ["telegram_id"],
            },
        },
    ]


def get_security_tools() -> list[dict[str, Any]]:
    """Get security tools for admin verification."""
    return [
        {
            "name": "check_username_spoofing",
            "description": "Проверить username на попытку маскировки под админа.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "@username"},
                    "telegram_id": {"type": "integer", "description": "Telegram ID (опционально)"},
                },
                "required": ["username"],
            },
        },
        {
            "name": "get_verified_admins",
            "description": "Получить список верифицированных админов.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "verify_admin_identity",
            "description": "Проверить личность админа по telegram_id.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "integer", "description": "Telegram ID"},
                    "username": {"type": "string", "description": "@username (опционально)"},
                },
                "required": ["telegram_id"],
            },
        },
    ]


def get_user_wallet_tools() -> list[dict[str, Any]]:
    """Get wallet tools for regular users (limited)."""
    return [
        {
            "name": "get_wallet_summary_for_dialog",
            "description": "Получить сводку кошелька для завершения диалога.",
            "input_schema": {
                "type": "object",
                "properties": {"user_telegram_id": {"type": "integer", "description": "Telegram ID"}},
                "required": ["user_telegram_id"],
            },
        },
    ]


def get_all_admin_tools(role: UserRole = UserRole.ADMIN) -> list[dict[str, Any]]:
    """
    Get all admin tools based on role.

    Args:
        role: User role

    Returns:
        List of all available tools for the role
    """
    tools = []

    # Basic admin tools
    tools.extend(get_messaging_tools(role))
    tools.extend(get_bonus_tools())
    tools.extend(get_appeals_tools())
    tools.extend(get_inquiries_tools())
    tools.extend(get_user_management_tools())
    tools.extend(get_statistics_tools())
    tools.extend(get_withdrawals_tools())
    tools.extend(get_deposits_tools())
    tools.extend(get_roi_tools())
    tools.extend(get_blacklist_tools())
    tools.extend(get_finpass_tools())
    tools.extend(get_wallet_tools())
    tools.extend(get_referral_tools())
    tools.extend(get_logs_tools())
    tools.extend(get_settings_tools())
    tools.extend(get_security_tools())

    # Super admin only tools
    if role == UserRole.SUPER_ADMIN:
        tools.extend(get_interview_tools())
        tools.extend(get_system_admin_tools())
        tools.extend(get_admin_management_tools())

    return tools
