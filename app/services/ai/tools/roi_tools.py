"""ROI corridor tools."""

from typing import Any


def get_roi_tools() -> list[dict[str, Any]]:
    """Get ROI corridor tools."""
    return [
        {
            "name": "get_roi_config",
            "description": "Получить конфигурацию ROI коридора.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": (
                            "Уровень (1-5) или пусто для всех"
                        ),
                    },
                },
                "required": [],
            },
        },
        {
            "name": "set_roi_corridor",
            "description": (
                "Установить ROI коридор для уровня. ТОЛЬКО ДОВЕРЕННЫЕ "
                "АДМИНЫ!"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Уровень (1-5)",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["custom", "equal"],
                        "description": "Режим",
                    },
                    "roi_min": {
                        "type": "number",
                        "description": "Мин. ROI %",
                    },
                    "roi_max": {
                        "type": "number",
                        "description": "Макс. ROI %",
                    },
                    "roi_fixed": {
                        "type": "number",
                        "description": "Фикс. ROI %",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина изменения",
                    },
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
                    "level": {
                        "type": "integer",
                        "description": "Уровень (1-5)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Макс. кол-во записей",
                    },
                },
                "required": [],
            },
        },
    ]
