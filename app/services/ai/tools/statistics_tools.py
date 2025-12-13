"""Platform statistics tools."""

from typing import Any


def get_statistics_tools() -> list[dict[str, Any]]:
    """Get platform statistics tools."""
    return [
        {
            "name": "get_deposit_stats",
            "description": "Получить статистику депозитов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_bonus_stats",
            "description": "Получить статистику бонусов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_withdrawal_stats",
            "description": "Получить статистику выводов.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_financial_report",
            "description": "Получить финансовый отчёт.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get_roi_stats",
            "description": "Получить статистику ROI.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]
